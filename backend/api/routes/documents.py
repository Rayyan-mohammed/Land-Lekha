from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import audit
from ..auth import current_user, require
from ..config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, STORAGE_DIR
from ..db import get_db
from ..models import Document, LandRecord, User
from ..processing import process_document
from ..schemas import DocumentDetail, DocumentSummary

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_visible(db: Session, doc_id: int, user: User) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    if user.role == "operator" and doc.uploaded_by != user.id:
        raise HTTPException(403, "operators can only see their own uploads")
    return doc


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentSummary)
async def upload(request: Request, background: BackgroundTasks, file: UploadFile = File(...),
                 db: Session = Depends(get_db), user: User = Depends(require("operator", "verifier"))):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"file larger than {MAX_UPLOAD_MB} MB")
    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.sha256 == sha, Document.status != "failed"))
    if existing:
        audit.log(db, "document.duplicate_upload", user, "document", existing.id, {"filename": file.filename}, request)
        db.commit()
        raise HTTPException(409, {"message": "this exact file was already uploaded", "document_id": existing.id})

    doc = Document(filename=file.filename or f"upload{ext}", stored_path="", sha256=sha, size_bytes=len(data),
                   uploaded_by=user.id, status="queued")
    db.add(doc)
    db.flush()
    folder = STORAGE_DIR / "documents" / str(doc.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"original{ext}"
    path.write_bytes(data)
    doc.stored_path = str(path)
    audit.log(db, "document.uploaded", user, "document", doc.id, {"filename": doc.filename, "bytes": len(data)}, request)
    db.commit()
    background.add_task(process_document, doc.id)
    return doc


@router.get("", response_model=dict)
def list_documents(status_: str | None = Query(None, alias="status"), district: str | None = None,
                   q: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Document)
    if user.role == "operator":
        stmt = stmt.where(Document.uploaded_by == user.id)
    if status_:
        stmt = stmt.where(Document.status.in_(status_.split(",")))
    if district:
        stmt = stmt.where(Document.district == district)
    if q:
        stmt = stmt.where(or_(Document.filename.ilike(f"%{q}%"), Document.district.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"total": total, "page": page, "page_size": page_size,
            "items": [DocumentSummary.model_validate(d).model_dump(mode="json") for d in rows]}


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = _get_visible(db, doc_id, user)
    out = DocumentDetail.model_validate(doc)
    ext = doc.extraction or {}
    out.consistency = ext.get("consistency", [])
    out.duplicates = ext.get("duplicates", [])
    out.threshold = ext.get("threshold")
    out.pages = [{"page": p["page"], "width": p["width"], "height": p["height"], "preprocess": p["preprocess"]}
                 for p in (doc.ocr or {}).get("pages", [])]
    out.uploader_name = doc.uploader.full_name if doc.uploader else None
    rec = db.scalar(select(LandRecord.id).where(LandRecord.document_id == doc.id))
    out.record_id = rec
    return out


@router.get("/{doc_id}/pages/{n}")
def page_image(doc_id: int, n: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Preprocessed page image; field bboxes are in this image's pixel space."""
    doc = _get_visible(db, doc_id, user)
    path = Path(doc.stored_path).parent / f"page-{n}.png"
    if not path.exists():
        raise HTTPException(404, "page image not available yet")
    return FileResponse(path, media_type="image/png")


@router.get("/{doc_id}/original")
def original_file(doc_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = _get_visible(db, doc_id, user)
    return FileResponse(doc.stored_path, filename=doc.filename)


@router.get("/{doc_id}/ocr")
def ocr_output(doc_id: int, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    doc = _get_visible(db, doc_id, user)
    return {"ocr": doc.ocr, "extraction": doc.extraction}


@router.post("/{doc_id}/reprocess", status_code=202, response_model=DocumentSummary)
def reprocess(doc_id: int, request: Request, background: BackgroundTasks, db: Session = Depends(get_db),
              user: User = Depends(require("admin"))):
    doc = _get_visible(db, doc_id, user)
    if doc.status in ("verified", "rejected"):
        raise HTTPException(409, "document already reviewed")
    doc.status = "queued"
    audit.log(db, "document.reprocess", user, "document", doc.id, None, request)
    db.commit()
    background.add_task(process_document, doc.id)
    return doc
