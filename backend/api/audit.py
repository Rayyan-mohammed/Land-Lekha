"""The audit trail, and what makes it hard to rewrite quietly.

Every entry carries a SHA-256 of its own contents chained to the hash of the entry before it.
Editing or deleting a row later leaves every later hash disagreeing with what it should be, and
`verify_chain` says exactly where. This is tamper-*evidence*, not tamper-proofing: somebody with
write access to the database and this source could recompute the whole chain. Making that
impossible needs the hashes signed or written somewhere the application cannot reach, which is
the honest next step if this is ever deployed for real.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import AuditLog, User

_chain_lock = threading.Lock()  # two requests must not chain onto the same row at once
_MAX_ATTEMPTS = 5


def _utc_text(ts) -> str | None:
    """One spelling of an instant. SQLite hands the timestamp back without its timezone, so a
    hash taken before the write would never match one taken after it."""
    if ts is None:
        return None
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.isoformat()


def row_digest(row: AuditLog, prev_hash: str | None) -> str:
    """The hash of one entry: its content, plus the entry before it."""
    payload = json.dumps({
        "ts": _utc_text(row.ts),
        "user_id": row.user_id, "username": row.username, "action": row.action,
        "entity_type": row.entity_type, "entity_id": row.entity_id,
        "details": row.details, "ip": row.ip, "prev": prev_hash or "",
    }, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log(db: Session, action: str, user: User | None = None, entity_type: str | None = None,
        entity_id: int | None = None, details: dict | None = None, request: Request | None = None) -> None:
    """Append an audit entry. Caller commits.

    `_chain_lock` only serializes threads in *this* process; with more than one replica
    sharing a database, two processes can still both read the same "last row" and both
    commit a hash chained to it, forking the chain (verify_chain then misreports the fork
    as tampering). A unique index on prev_hash (db.py's ensure_unique_audit_chain) makes the
    database itself refuse the second writer's flush; the retry here reads the new last row
    and tries again, inside a SAVEPOINT so only this entry's insert is rolled back on a
    collision - not whatever else the caller already added to this transaction."""
    for attempt in range(_MAX_ATTEMPTS):
        entry = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action, entity_type=entity_type, entity_id=entity_id, details=details,
            ip=request.client.host if request and request.client else None,
        )
        try:
            with _chain_lock, db.begin_nested():
                last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
                db.add(entry)
                db.flush()  # gives the row its ts default and id
                entry.prev_hash = last.row_hash if last else None
                entry.row_hash = row_digest(entry, entry.prev_hash)
                db.flush()  # the unique index on prev_hash catches a concurrent racer here
            return
        except IntegrityError:
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            continue


def verify_chain(db: Session, limit: int | None = None) -> dict:
    """Walk the trail and report the first entry that no longer matches its own hash.

    Entries written before this was added carry no hash; they are counted and skipped rather
    than reported as tampering."""
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.id)))
    if limit:
        rows = rows[-limit:]
    checked = unhashed = 0
    prev = None
    for row in rows:
        if row.row_hash is None:
            unhashed += 1
            prev = None
            continue
        expected = row_digest(row, row.prev_hash)
        if expected != row.row_hash:
            return {"ok": False, "checked": checked, "unhashed": unhashed, "broken_at": row.id,
                    "detail": "this entry's contents no longer match its hash"}
        if prev is not None and row.prev_hash != prev:
            return {"ok": False, "checked": checked, "unhashed": unhashed, "broken_at": row.id,
                    "detail": "an entry is missing between this one and the one before it"}
        prev = row.row_hash
        checked += 1
    return {"ok": True, "checked": checked, "unhashed": unhashed, "broken_at": None, "detail": "the chain is intact"}
