"""Human-in-the-loop verification."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.extraction import gazetteer
from backend.extraction.confidence import default_threshold
from backend.extraction.schema import FIELD_MAP, REQUIRED_FIELDS
from backend.extraction.validate import PARSERS, Parsed, parse_area

from .. import audit
from ..auth import require
from ..config import AUTO_ACCEPT_THRESHOLD
from ..db import get_db
from ..models import Correction, Document, ExtractedField, User, utcnow
from ..notifications import notify_document_reviewed
from ..processing import invalidate_memory, upsert_record
from ..schemas import DocumentSummary, VerifyIn

router = APIRouter(prefix="/api", tags=["review"])


class QueueItem(DocumentSummary):
    flagged: int = 0  # fields a verifier should look at: still pending, below the threshold or failing a rule


def flagged_counts(db: Session, doc_ids: list[int]) -> dict[int, int]:
    """Per document, the fields a verifier should look at (the same rule as the review screen)."""
    if not doc_ids:
        return {}
    thr = AUTO_ACCEPT_THRESHOLD or default_threshold()
    return dict(db.execute(
        select(ExtractedField.document_id, func.count())
        .where(ExtractedField.document_id.in_(doc_ids), ExtractedField.status == "pending",
               or_(ExtractedField.confidence < thr, ExtractedField.valid.is_(False)))
        .group_by(ExtractedField.document_id)).all())


@router.get("/review/queue", response_model=list[QueueItem])
def queue(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """Documents waiting for a human, lowest confidence first, with how many fields each needs checked."""
    docs = list(db.scalars(select(Document).where(Document.status == "needs_review")
                           .order_by(Document.overall_confidence.asc().nulls_first(), Document.created_at).limit(limit)))
    counts = flagged_counts(db, [d.id for d in docs])
    out = []
    for d in docs:
        item = QueueItem.model_validate(d)
        item.flagged = counts.get(d.id, 0)
        out.append(item)
    return out


def _reparse(name: str, value: str, state: str | None):
    """Normalise a verifier-typed value the same way extraction would."""
    if name == "plot_area":
        info = gazetteer.state_info(state) if state else None
        return parse_area(value, None, info["bigha_ha"] if info else 0.2529)
    if name in ("village", "tehsil", "district", "state"):
        place, score = gazetteer.best_match(name, value)
        if place is not None and score >= 0.85:
            return Parsed(place.en, score, [], {"en": place.en, "hi": place.hi})
        return None
    if name in PARSERS:
        return PARSERS[name](value)
    return None


@router.post("/documents/{doc_id}/verify")
def verify(doc_id: int, body: VerifyIn, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require("verifier"))):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    if doc.status not in ("needs_review", "auto_accepted"):
        raise HTTPException(409, f"document is '{doc.status}', cannot be verified")
    unknown = [n for n in body.fields if n not in FIELD_MAP]
    if unknown:
        raise HTTPException(422, f"unknown fields: {unknown}")

    by_name = {f.name: f for f in doc.fields}
    changes = []
    for name, dec in body.fields.items():
        f = by_name.get(name)
        if dec.action == "correct":
            value = (dec.value or "").strip()
            if not value:
                raise HTTPException(422, f"value required to correct {name}")
            if f is None:  # field the machine missed entirely
                f = ExtractedField(name=name, value=None, raw_value=None, confidence=0.0, valid=False, issues=[],
                                   source="manual", status="pending")
                doc.fields.append(f)
                by_name[name] = f
            db.add(Correction(document_id=doc.id, field_name=name, raw_value=f.raw_value,
                              extracted_value=f.value, corrected_value=value, user_id=user.id))
            changes.append({"field": name, "from": f.value, "to": value})
            parsed = _reparse(name, value, doc.state)
            f.value = parsed.value if parsed and parsed.value else value
            if parsed and parsed.normalized:
                f.normalized = parsed.normalized
            f.valid = True
            f.status = "corrected"
            f.confidence = 1.0
        elif dec.action == "reject":
            if f is None:
                continue
            f.status = "rejected"
            changes.append({"field": name, "rejected": f.value})
        else:
            if f is None:
                continue
            f.status = "confirmed"
    for f in doc.fields:
        if f.status in ("pending", "auto"):
            f.status = "confirmed"

    if body.decision == "approve":
        present = {f.name for f in doc.fields if f.status != "rejected" and f.value}
        missing = [n for n in REQUIRED_FIELDS if n not in present]
        if missing:
            raise HTTPException(422, f"cannot approve, required fields missing: {missing}")
        doc.status = "verified"
        db.flush()
        upsert_record(db, doc, verification="human")
    else:
        doc.status = "rejected"
    doc.review_note = body.note
    doc.reviewed_by = user.id
    doc.reviewed_at = utcnow()
    audit.log(db, f"document.{'verified' if body.decision == 'approve' else 'rejected'}", user, "document", doc.id,
              {"changes": changes, "note": body.note}, request)
    db.commit()
    invalidate_memory()
    notify_document_reviewed(uploader_email=None, uploader_name=doc.uploader.full_name if doc.uploader else "operator",
                             document_id=doc.id, status=doc.status, reviewer_name=user.full_name, note=doc.review_note)
    return {"id": doc.id, "status": doc.status, "changes": changes}
