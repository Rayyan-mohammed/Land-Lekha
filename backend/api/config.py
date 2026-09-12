"""Runtime settings, read from environment variables (or a .env file in the repo root)."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

STORAGE_DIR = Path(os.getenv("LL_STORAGE_DIR", ROOT / "storage"))
DATABASE_URL = os.getenv("LL_DATABASE_URL", f"sqlite:///{(STORAGE_DIR / 'landlekha.sqlite3').as_posix()}")
JWT_SECRET_SET = bool(os.getenv("LL_JWT_SECRET"))


def _jwt_secret() -> str:
    """The signing key. Set LL_JWT_SECRET in anything but a demo.

    Without it the key used to be random per process, which is fine for one `uvicorn` but
    quietly breaks the moment there is more than one: `--workers 4`, or two containers behind
    a load balancer, each mint tokens the others reject, and users see random 401s. So when
    the variable is absent the key is generated once and kept in the storage directory, which
    every worker on that machine shares. It is still only a fallback - across machines, set
    the variable (docker-compose.yml already insists on it)."""
    from_env = os.getenv("LL_JWT_SECRET")
    if from_env:
        return from_env
    keyfile = STORAGE_DIR / "jwt_secret"
    try:
        if keyfile.exists():
            saved = keyfile.read_text(encoding="utf-8").strip()
            if saved:
                return saved
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        generated = secrets.token_hex(32)
        keyfile.write_text(generated, encoding="utf-8")
        try:
            keyfile.chmod(0o600)
        except OSError:
            pass  # windows, or a filesystem without permissions
        return generated
    except OSError:
        return secrets.token_hex(32)  # read-only storage: one process only, as before


JWT_SECRET = _jwt_secret()
JWT_EXPIRE_MINUTES = int(os.getenv("LL_JWT_EXPIRE_MINUTES", "720"))
# a document stuck in "processing" this long on startup is treated as crashed, not as another
# live replica's in-flight work, and is reclaimed; see backend/api/main.py's _init_db
STALE_PROCESSING_MINUTES = int(os.getenv("LL_STALE_PROCESSING_MINUTES", "15"))
# unset -> use the threshold chosen during calibration (backend/extraction/master/calibration.json)
AUTO_ACCEPT_THRESHOLD = float(os.environ["LL_AUTO_ACCEPT_THRESHOLD"]) if os.getenv("LL_AUTO_ACCEPT_THRESHOLD") else None
OCR_ENGINE = os.getenv("LL_OCR_ENGINE", "easyocr")
MAX_UPLOAD_MB = int(os.getenv("LL_MAX_UPLOAD_MB", "20"))
# A 20 MB file can still decode to billions of pixels ("decompression bomb"). OCR runs in one
# shared worker thread, so an out-of-memory there takes down every other document with it.
MAX_IMAGE_PIXELS = int(os.getenv("LL_MAX_IMAGE_PIXELS", "60000000"))  # 60 MP ~ a 9000x6600 scan
SEED_DEMO_USERS = os.getenv("LL_SEED_DEMO_USERS", "1") == "1"
CORS_ORIGINS = [o.strip() for o in os.getenv("LL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"}
