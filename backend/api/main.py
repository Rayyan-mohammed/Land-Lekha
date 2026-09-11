"""LandLekha API.

    uvicorn backend.api.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .auth import hash_password
from .config import CORS_ORIGINS, ROOT, SEED_DEMO_USERS
from .db import Base, SessionLocal, engine
from .models import Document, User
from .routes import admin, auth, documents, integration, review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("landlekha")

DEMO_USERS = [
    ("admin", "Admin User", "admin", "admin@123"),
    ("verifier", "Verifier (Tehsil)", "verifier", "verify@123"),
    ("operator", "Field Operator", "operator", "upload@123"),
]


def _init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if SEED_DEMO_USERS and db.scalar(select(User).limit(1)) is None:
            for username, name, role, pw in DEMO_USERS:
                db.add(User(username=username, full_name=name, role=role, password_hash=hash_password(pw)))
            log.warning("seeded demo users (admin / verifier / operator) - change passwords outside the demo")
        # documents interrupted by a restart go back to the queue
        stuck = list(db.scalars(select(Document).where(Document.status.in_(("queued", "processing")))))
        for d in stuck:
            d.status = "queued"
        db.commit()
    if stuck:
        from .processing import enqueue

        for d in stuck:
            enqueue(d.id)


def _warm_ocr() -> None:
    try:
        from backend.ocr.engine import get_engine

        from .config import OCR_ENGINE
        get_engine(OCR_ENGINE)
        log.info("OCR engine ready")
    except Exception:  # noqa: BLE001
        log.exception("OCR engine failed to load")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _init_db()
    threading.Thread(target=_warm_ocr, daemon=True).start()
    yield


app = FastAPI(title="LandLekha API", version="0.1.0", lifespan=lifespan,
              description="AI-powered land record digitization and validation — SIH 2026 PS 26018")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, documents.router, review.router, admin.router, integration.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    from backend.ocr import engine as ocr_engine

    from .processing import queue_length

    return {"status": "ok", "ocr_ready": bool(ocr_engine._engines), "queue": queue_length()}


# serve the built frontend (npm run build) from the same origin, if present
_dist = ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = _dist / path
        return FileResponse(f if path and f.is_file() else _dist / "index.html")
