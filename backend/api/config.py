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
JWT_SECRET = os.getenv("LL_JWT_SECRET") or secrets.token_hex(32)  # random per run if not set
JWT_EXPIRE_MINUTES = int(os.getenv("LL_JWT_EXPIRE_MINUTES", "720"))
# a document stuck in "processing" this long on startup is treated as crashed, not as another
# live replica's in-flight work, and is reclaimed; see backend/api/main.py's _init_db
STALE_PROCESSING_MINUTES = int(os.getenv("LL_STALE_PROCESSING_MINUTES", "15"))
# unset -> use the threshold chosen during calibration (backend/extraction/master/calibration.json)
AUTO_ACCEPT_THRESHOLD = float(os.environ["LL_AUTO_ACCEPT_THRESHOLD"]) if os.getenv("LL_AUTO_ACCEPT_THRESHOLD") else None
OCR_ENGINE = os.getenv("LL_OCR_ENGINE", "easyocr")
MAX_UPLOAD_MB = int(os.getenv("LL_MAX_UPLOAD_MB", "20"))
SEED_DEMO_USERS = os.getenv("LL_SEED_DEMO_USERS", "1") == "1"
CORS_ORIGINS = [o.strip() for o in os.getenv("LL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"}
