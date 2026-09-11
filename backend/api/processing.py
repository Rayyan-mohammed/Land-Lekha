"""Document processing: file -> OCR -> extraction -> DB, plus record creation on approval."""
from __future__ import annotations

import logging
import threading
import time
import traceback
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.extraction.extractor import extract
from backend.extraction.learning import CorrectionMemory
from backend.ocr.pipeline import run_ocr

from . import audit
from .config import AUTO_ACCEPT_THRESHOLD, OCR_ENGINE
from .db import SessionLocal
from .models import Correction, Document, ExtractedField, LandRecord, utcnow

log = logging.getLogger("landlekha.processing")

RECORD_FIELDS = ["owner_name", "father_name", "khata_number", "khasra_number", "survey_number", "plot_area",
                 "land_classification", "village", "tehsil", "district", "state", "mutation_number",
                 "mutation_date", "registration_number", "registration_date"]

_memory: CorrectionMemory | None = None
_memory_lock = threading.Lock()


def get_memory(db: Session) -> CorrectionMemory:
    """Learning memory rebuilt from stored corrections and review outcomes."""
    global _memory
    with _memory_lock:
        if _memory is None:
            mem = CorrectionMemory()
            for c in db.scalars(select(Correction)):
                mem.add_correction(c.field_name, c.raw_value, c.corrected_value)
            reviewed = db.scalars(select(ExtractedField).where(ExtractedField.status.in_(("confirmed", "corrected"))))
            for f in reviewed:
                mem.add_review(f.name, f.status == "corrected")
            _memory = mem
        return _memory


def invalidate_memory() -> None:
    global _memory
    with _memory_lock:
        _memory = None


def existing_records(db: Session, district: str | None, village: str | None, exclude_doc: int) -> list[dict]:
    if not district or not village:
        return []
    rows = db.scalars(select(LandRecord).where(LandRecord.district == district, LandRecord.village == village))
    return [{"record_id": r.id, "document_id": r.document_id, **{f: getattr(r, f) for f in RECORD_FIELDS}}
            for r in rows if r.document_id != exclude_doc]


def process_document(doc_id: int) -> None:
    """Runs in a worker thread. Never raises; failures are stored on the document."""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        doc.status = "processing"
        db.commit()
        t0 = time.perf_counter()
        path = Path(doc.stored_path)
        ocr = run_ocr(path.read_bytes(), doc.filename, out_dir=path.parent, engine=OCR_ENGINE)

        # first pass without duplicates to learn the location, then check duplicates in that village
        memory = get_memory(db)
        ext = extract(ocr, memory=memory, threshold=AUTO_ACCEPT_THRESHOLD)
        district = ext["fields"].get("district", {}).get("value")
        village = ext["fields"].get("village", {}).get("value")
        others = existing_records(db, district, village, doc.id)
        if others:
            ext = extract(ocr, memory=memory, existing_records=others, threshold=AUTO_ACCEPT_THRESHOLD)

        doc.ocr = ocr
        doc.extraction = ext
        doc.page_count = len(ocr["pages"])
        doc.document_type = ext["document_type"]
        doc.overall_confidence = ext["overall_confidence"]
        doc.route_reasons = ext["route_reasons"]
        doc.state = ext["fields"].get("state", {}).get("value")
        doc.district = district
        doc.fields.clear()
        db.flush()
        auto = ext["route"] == "auto_accept"
        for name, f in ext["fields"].items():
            doc.fields.append(ExtractedField(
                name=name, value=f["value"], raw_value=f["raw"], normalized=f.get("normalized"),
                confidence=f["confidence"], ocr_confidence=f["ocr_confidence"], valid=f["valid"],
                issues=f["issues"], page=f["page"], bbox=f["bbox"], source=f["source"],
                status="auto" if auto else "pending", original_value=f["value"],
            ))
        doc.status = "auto_accepted" if auto else "needs_review"
        doc.processing_ms = int((time.perf_counter() - t0) * 1000)
        doc.processed_at = utcnow()
        doc.error = None
        db.flush()
        if auto:
            upsert_record(db, doc, verification="auto")
        audit.log(db, "document.processed", None, "document", doc.id,
                  {"route": ext["route"], "confidence": ext["overall_confidence"], "ms": doc.processing_ms,
                   "reasons": ext["route_reasons"][:5]})
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("processing failed for document %s", doc_id)
        doc = db.get(Document, doc_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = f"{type(exc).__name__}: {exc}"
            audit.log(db, "document.failed", None, "document", doc_id, {"error": doc.error,
                                                                         "trace": traceback.format_exc()[-1500:]})
            db.commit()
    finally:
        db.close()


def upsert_record(db: Session, doc: Document, verification: str) -> LandRecord:
    values = {f.name: f.value for f in doc.fields if f.status != "rejected"}
    rec = db.scalar(select(LandRecord).where(LandRecord.document_id == doc.id)) or LandRecord(document_id=doc.id)
    for name in RECORD_FIELDS:
        setattr(rec, name, values.get(name))
    area = next((f for f in doc.fields if f.name == "plot_area" and f.status != "rejected"), None)
    rec.area_hectares = (area.normalized or {}).get("hectares") if area else None
    rec.verification = verification
    db.add(rec)
    return rec
