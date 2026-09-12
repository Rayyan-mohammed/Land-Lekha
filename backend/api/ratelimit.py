"""Login brute-force throttling.

In-memory sliding-window limiter, keyed by (client IP, username). This is a real gap:
the login endpoint previously had no protection against password guessing at all. An
in-memory store is correct for this prototype's single-process deployment; a real
multi-worker/multi-instance deployment needs a shared store (Redis, e.g.) instead - that
swap is the one thing this module doesn't do, and is called out below rather than faked.
"""
from __future__ import annotations

import threading
import time

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 min
LOCKOUT_SECONDS = 300  # 5 min

_lock = threading.Lock()
_attempts: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}


def _key(ip: str, username: str) -> str:
    return f"{ip}:{username.lower()}"


def check(ip: str, username: str) -> float | None:
    """Returns seconds remaining if locked out, else None."""
    key = _key(ip, username)
    now = time.time()
    with _lock:
        until = _locked_until.get(key)
        if until and until > now:
            return until - now
        if until:
            _locked_until.pop(key, None)
            _attempts.pop(key, None)
    return None


def record_failure(ip: str, username: str) -> None:
    key = _key(ip, username)
    now = time.time()
    with _lock:
        hits = [t for t in _attempts.get(key, []) if now - t < WINDOW_SECONDS]
        hits.append(now)
        _attempts[key] = hits
        if len(hits) >= MAX_ATTEMPTS:
            _locked_until[key] = now + LOCKOUT_SECONDS


def record_success(ip: str, username: str) -> None:
    key = _key(ip, username)
    with _lock:
        _attempts.pop(key, None)
        _locked_until.pop(key, None)
