"""LandLekha API.

    uvicorn backend.api.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select

from .auth import hash_password
from .config import CORS_ORIGINS, JWT_SECRET_SET, ROOT, SEED_DEMO_USERS, STALE_PROCESSING_MINUTES
from .db import Base, SessionLocal, engine, upgrade_schema
from .graphql_api import graphql_router
from .models import Document, User
from .routes import admin, auth, documents, integration, public, review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("landlekha")

DEMO_USERS = [
    ("admin", "Admin User", "admin", "admin@123"),
    ("verifier", "Verifier (Tehsil)", "verifier", "verify@123"),
    ("operator", "Field Operator", "operator", "upload@123"),
]


def _init_db() -> None:
    if not JWT_SECRET_SET:
        log.warning("LL_JWT_SECRET is not set - using a random secret for this process only. Fine for a single "
                    "process; running more than one (docker-compose --scale, multiple uvicorn workers) without "
                    "setting it means each process verifies tokens with a different secret and logins randomly 401.")
    Base.metadata.create_all(engine)
    added = upgrade_schema()
    if added:
        log.warning("database upgraded, added columns: %s", ", ".join(added))
    with SessionLocal() as db:
        if SEED_DEMO_USERS and db.scalar(select(User).limit(1)) is None:
            for username, name, role, pw in DEMO_USERS:
                db.add(User(username=username, full_name=name, role=role, password_hash=hash_password(pw)))
            log.warning("seeded demo users (admin / verifier / operator) - change passwords outside the demo")
        # "queued" documents are always safe to re-enqueue: claim_document()'s atomic
        # UPDATE means at most one worker ever wins a queued document, in this process or
        # another replica. "processing" is different - with more than one replica sharing
        # this database, another replica may be mid-flight on it right now, so only a
        # document that has been "processing" for implausibly long (a crash, not a slow
        # page) is reclaimed here.
        stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_PROCESSING_MINUTES)
        stuck = list(db.scalars(select(Document).where(
            or_(Document.status == "queued",
                (Document.status == "processing")
                & or_(Document.processing_started_at.is_(None), Document.processing_started_at < stale_cutoff)))))
        for d in stuck:
            if d.status == "processing":
                log.warning("reclaiming document %s: stuck in 'processing' since %s", d.id, d.processing_started_at)
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

for r in (auth.router, documents.router, review.router, admin.router, integration.router, public.router):
    app.include_router(r)
app.include_router(graphql_router, tags=["integration (mock external systems)"])


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
