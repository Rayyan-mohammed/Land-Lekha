from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL, STORAGE_DIR

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
    """Add columns that the models define but an existing database does not have yet.

    `create_all()` creates missing tables but never alters existing ones, so after a
    model gains a column (e.g. documents.owners) an older database fails with "no such
    column" on startup. This adds new *nullable* columns in place (SQLite and Postgres);
    anything else (renames, NOT NULL without default, type changes) needs a real migration.
    Returns the columns added, as "table.column".

    With more than one replica sharing a Postgres database (docker-compose --scale), every
    replica calls this on startup. A `pg_advisory_xact_lock` serializes them so only one
    replica actually runs the ALTER TABLEs; the rest block until it commits, then see every
    column already present and add nothing - no "column already exists" race. SQLite has no
    equivalent, but it isn't used with more than one process anyway."""
    bind = bind or engine
    quote = bind.dialect.identifier_preparer.quote
    added = []
    with bind.begin() as conn:
        if bind.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(727277001)"))
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


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
