"""Test-wide setup: never touch a developer's real database or uploads.

Runs before any test module imports the backend (config reads these at import time).
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="landlekha-tests-")
os.environ["LL_STORAGE_DIR"] = _tmp
os.environ.pop("LL_DATABASE_URL", None)
os.environ.setdefault("LL_JWT_SECRET", "test-secret-" + "x" * 32)
os.environ["LL_SEED_DEMO_USERS"] = "1"
