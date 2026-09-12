from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL, STORAGE_DIR

log = logging.getLogger("landlekha")

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if _sqlite else {}, pool_pre_ping=True)

if _sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def upgrade_schema(bind: Engine | None = None) -> list[str]:
    """Create any missing tables, then add columns that the models define but an existing
    table does not have yet.

    `create_all()` creates missing tables but never alters existing ones, so after a
    model gains a column (e.g. documents.owners) an older database fails with "no such
    column" on startup. This adds new *nullable* columns in place (SQLite and Postgres);
    anything else (renames, NOT NULL without default, type changes) needs a real migration.
    Returns the columns added, as "table.column".

    With more than one replica sharing a Postgres database (docker-compose --scale), every
    replica calls this on startup. A `pg_advisory_xact_lock` serializes them so only one
    replica actually runs the CREATE/ALTER TABLEs; the rest block until it commits, then
    see every table and column already present and do nothing - no "already exists" race
    on a brand-new database either (create_all() runs inside the same lock, not before it;
    a table added by a fresh model - e.g. login_attempts - used to race here). SQLite has
    no equivalent, but it isn't used with more than one process anyway."""
    bind = bind or engine
    quote = bind.dialect.identifier_preparer.quote
    added = []
    with bind.begin() as conn:
        if bind.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(727277001)"))
        Base.metadata.create_all(conn)
        insp = inspect(conn)  # inspect via this connection: consistent with the lock above
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue  # create_all makes it with every column
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                if not col.nullable and col.server_default is None:
                    raise RuntimeError(f"cannot add NOT NULL column {table.name}.{col.name} automatically; "
                                       "write a migration")
                conn.execute(text(f"ALTER TABLE {quote(table.name)} ADD COLUMN {quote(col.name)} "
                                  f"{col.type.compile(dialect=bind.dialect)}"))
                added.append(f"{table.name}.{col.name}")
    return added


def ensure_unique_active_document(bind: Engine | None = None) -> bool:
    """One live document per file, enforced by the database rather than by a lookup.

    The upload endpoint checks for an existing sha256 before inserting, which leaves a gap:
    two uploads of the same file at the same moment both pass the check and both insert. A
    partial unique index closes it - "failed" documents are left out so a file that failed to
    process can be sent again. Returns False when the index cannot be created, which means an
    older database already holds duplicates; the pre-check still applies there."""
    bind = bind or engine
    try:
        with bind.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_sha256_active "
                              "ON documents (sha256) WHERE status != 'failed'"))
        return True
    except Exception as exc:  # duplicates already stored, or a backend without partial indexes
        log.warning("could not enforce one-live-document-per-file: %s", exc)
        return False


def ensure_unique_audit_chain(bind: Engine | None = None) -> bool:
    """Each audit entry names the row it chains onto (prev_hash); this makes the database
    itself refuse a second entry chaining onto the same one. Without it, two requests
    logging an entry at the same moment can both read the same "last row", both compute a
    hash chained to it, and both commit - forking the chain, which verify_chain() then
    misreports as tampering. NULL prev_hash (the very first entry, and rows written before
    hashing existed) is unrestricted: unique indexes allow any number of NULLs."""
    bind = bind or engine
    try:
        with bind.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_audit_log_prev_hash ON audit_log (prev_hash)"))
        return True
    except Exception as exc:  # noqa: BLE001 - an older database already holds a fork
        log.warning("could not enforce a single audit chain: %s", exc)
        return False


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
