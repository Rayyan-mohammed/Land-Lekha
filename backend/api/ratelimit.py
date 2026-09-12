"""Login brute-force throttling.

Backed by the `login_attempts` table (see models.py) rather than an in-memory dict, so
the lockout is shared across every replica behind a load balancer (docker-compose
--scale api=N) - a process-local store would let an attacker get MAX_ATTEMPTS guesses
per replica instead of in total, and a lockout on one replica wouldn't apply to the
others. Uses a fixed window (not a true sliding window like the in-memory version this
replaced): acceptable for a login endpoint, and simple enough to do safely as one
upsert-by-primary-key row instead of a scan over per-attempt timestamps.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import LoginAttempt, utcnow

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 min
LOCKOUT_SECONDS = 300  # 5 min


def _key(ip: str, username: str) -> str:
    return f"{ip}:{username.lower()}"


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes even from a DateTime(timezone=True) column
    # (Postgres doesn't); utcnow() always stores UTC, so a naive value is UTC too
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check(db: Session, ip: str, username: str) -> float | None:
    """Returns seconds remaining if locked out, else None."""
    row = db.get(LoginAttempt, _key(ip, username))
    if row is None:
        return None
    now = utcnow()
    if row.locked_until and _aware(row.locked_until) > now:
        return (_aware(row.locked_until) - now).total_seconds()
    if row.locked_until:  # lockout expired: clear it so a stale row doesn't linger forever
        db.delete(row)
        db.commit()
    return None


def record_failure(db: Session, ip: str, username: str) -> None:
    key = _key(ip, username)
    now = utcnow()
    row = db.get(LoginAttempt, key)
    if row is None or (now - _aware(row.window_started_at)).total_seconds() > WINDOW_SECONDS:
        row = row or LoginAttempt(key=key)
        row.count = 0
        row.window_started_at = now
        row.locked_until = None
    row.count += 1
    if row.count >= MAX_ATTEMPTS:
        row.locked_until = now + timedelta(seconds=LOCKOUT_SECONDS)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # another replica's concurrent failed attempt for the same (ip, username) inserted
        # the row first - harmless race, that row already records this window's failure
        db.rollback()


def record_success(db: Session, ip: str, username: str) -> None:
    row = db.get(LoginAttempt, _key(ip, username))
    if row:
        db.delete(row)
        db.commit()
