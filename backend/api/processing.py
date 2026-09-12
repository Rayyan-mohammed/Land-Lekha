"""Document processing: file -> OCR -> extraction -> DB, plus record creation on approval."""
from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.extraction.extractor import extract
from backend.extraction.learning import CorrectionMemory
from backend.classify import classify
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

# One worker thread per process runs documents in upload order. OCR is CPU-bound and the
# engine is shared, so parallel threads within a process would only wait on each other.
#
# Scaling out means running more than one API replica against the same (Postgres)
# database. Each replica's queue.Queue only holds doc_ids it learned about locally - a
# document uploaded to replica A never reaches replica B's in-memory queue - so a poller
# thread in every replica also scans the database for anything left "queued" and feeds it
# to that replica's own worker. Two replicas racing to pick up the same row is resolved by
# an atomic conditional UPDATE (claim_document): only the replica whose UPDATE actually
# matched the row moves on to process it, so double-processing can't happen even though
# both replicas will try.
_queue: queue.Queue[int] = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()
_poller: threading.Thread | None = None
_poller_lock = threading.Lock()
POLL_INTERVAL_SECONDS = 5


def _work() -> None:
    while True:
        doc_id = _queue.get()
        try:
            process_document(doc_id)
        finally:
            _queue.task_done()


def _poll() -> None:
    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            db = SessionLocal()
            try:
                ids = list(db.scalars(select(Document.id).where(Document.status == "queued")))
            finally:
                db.close()
            for doc_id in ids:
                _queue.put(doc_id)
        except Exception:  # noqa: BLE001 - a poll failure must not kill the poller
            log.exception("queue poll failed")


def enqueue(doc_id: int) -> None:
    global _worker, _poller
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_work, name="landlekha-worker", daemon=True)
            _worker.start()
    with _poller_lock:
        if _poller is None or not _poller.is_alive():
            _poller = threading.Thread(target=_poll, name="landlekha-queue-poller", daemon=True)
            _poller.start()
    _queue.put(doc_id)


def queue_length() -> int:
    return _queue.qsize()


def claim_document(db: Session, doc_id: int) -> bool:
    """Atomically moves one document from queued -> processing. Returns whether *this*
    caller won the claim - false means another worker (in this process or another
    replica) already picked it up, and processing it again would be wasted or wrong."""
    result = db.execute(update(Document).where(Document.id == doc_id, Document.status == "queued")
                        .values(status="processing", processing_started_at=utcnow()))
    db.commit()
    return result.rowcount > 0


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
    return [{"record_id": r.id, "document_id": r.document_id, "owners": r.owners, "parcels": r.parcels,
             **{f: getattr(r, f) for f in RECORD_FIELDS}}
            for r in rows if r.document_id != exclude_doc]


def process_document(doc_id: int) -> None:
    """Runs in a worker thread. Never raises; failures are stored on the document."""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        if not claim_document(db, doc_id):
            return  # already claimed by another worker/replica
        db.refresh(doc)
        t0 = time.perf_counter()
        path = Path(doc.stored_path)
        ocr = run_ocr(path.read_bytes(), doc.filename, out_dir=path.parent, engine=OCR_ENGINE)

        # Is this a land record at all? Decided from what was read, before anything is
        # extracted, so a bill or a marksheet never comes back wearing a khasra number.
        text = chr(10).join(l["text"] for pg in ocr["pages"] for l in pg.get("lines", []))
        worst = min((pg.get("quality", {}).get("verdict", "good") for pg in ocr["pages"]),
                    key=lambda v: {"poor": 0, "fair": 1, "good": 2}.get(v, 2), default="good")
        verdict = classify(text, tokens=sum(len(pg.get("tokens", [])) for pg in ocr["pages"]), quality=worst)
        doc.classification = verdict
        doc.ocr = ocr
        doc.page_count = len(ocr["pages"])
        if verdict["is_land_document"] is False:  # None means "could not tell": that page goes on to review
            doc.status = "not_land"
            doc.document_type = None
            doc.extraction = None
            doc.overall_confidence = None
            doc.route_reasons = [f"not a land document: {verdict['reason']}"]
            doc.fields.clear()
            doc.processing_ms = int((time.perf_counter() - t0) * 1000)
            doc.processed_at = utcnow()
            doc.error = None
            audit.log(db, "document.not_land", None, "document", doc.id,
                      {"confidence": verdict["confidence"], "reason": verdict["reason"], "ms": doc.processing_ms})
            db.commit()
            return

        # first pass without duplicates to learn the location, then check duplicates in that village
        memory = get_memory(db)
        ext = extract(ocr, memory=memory, threshold=AUTO_ACCEPT_THRESHOLD)
        district = ext["fields"].get("district", {}).get("value")
        village = ext["fields"].get("village", {}).get("value")
        others = existing_records(db, district, village, doc.id)
        if others:
            ext = extract(ocr, memory=memory, existing_records=others, threshold=AUTO_ACCEPT_THRESHOLD)

        doc.extraction = ext
        # the classifier names deed types the extractor does not know; keep its answer when it has one
        doc.document_type = (verdict["document_type"] if verdict["document_type"] not in (None, "unknown")
                             else ext["document_type"])
        doc.overall_confidence = ext["overall_confidence"]
        doc.route_reasons = ext["route_reasons"]
        doc.owners = ext.get("owners")
        doc.parcels = ext.get("parcels")
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
    rec.owners = doc.owners
    rec.parcels = doc.parcels
    rec.verification = verification
    db.add(rec)
    return rec
