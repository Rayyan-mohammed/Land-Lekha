"""Login brute-force throttling: after enough failed attempts from one client for one
username, further attempts (even correct ones) are rejected with 429 until the lockout
window passes. Backed by the login_attempts table (see ratelimit.py), so it works the
same way across multiple replicas sharing one database, not just one process."""
from fastapi.testclient import TestClient

from backend.api import ratelimit
from backend.api.db import SessionLocal
from backend.api.main import app
from backend.api.models import LoginAttempt


def _clear_attempts():
    with SessionLocal() as db:
        db.query(LoginAttempt).delete()
        db.commit()


def test_login_lockout_after_repeated_failures():
    with TestClient(app) as client:
        _clear_attempts()  # after the app's startup has created the table
        for _ in range(ratelimit.MAX_ATTEMPTS):
            r = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
            assert r.status_code == 401
        locked = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
        assert locked.status_code == 429
        # even the correct password is rejected while locked out
        still_locked = client.post("/api/auth/login", data={"username": "admin", "password": "admin@123"})
        assert still_locked.status_code == 429
        # a different username from the same client is unaffected
        other = client.post("/api/auth/login", data={"username": "verifier", "password": "verify@123"})
        assert other.status_code == 200
    _clear_attempts()
