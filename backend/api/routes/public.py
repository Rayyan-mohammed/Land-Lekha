"""Verified extracts and their public (no login) verification.

A bank, court or citizen scanning the QR code on a printed extract lands on
GET /api/public/records/{id}/verify?fp=..., which says whether the paper still matches
the official record.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import audit
from ..auth import current_user
from ..db import get_db
from ..fingerprint import fingerprint, record_content, short
from ..models import LandRecord, User, utcnow

router = APIRouter(tags=["verified extracts"])


@router.get("/api/records/{record_id}/extract")
def extract(record_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Data for a printable verified extract (the UI renders and prints it)."""
    r = db.get(LandRecord, record_id)
    if r is None:
        raise HTTPException(404, "record not found")
    fp = fingerprint(r)
    audit.log(db, "record.extract_issued", user, "land_record", r.id, {"fingerprint": short(fp)}, request)
    db.commit()
    return {
        "record": record_content(r),
        "area_hectares": r.area_hectares,
        "verification": r.verification,
        "source_document_id": r.document_id,
        "lrms_ref": r.lrms_ref,
        "fingerprint": fp,
        "fingerprint_short": short(fp),
        "verify_path": f"/verify/{r.id}?fp={fp}",
        "issued_at": utcnow().isoformat(),
        "issued_by": user.full_name,
    }


@router.get("/api/public/records/{record_id}/verify")
def verify(record_id: int, fp: str, db: Session = Depends(get_db)):
    """Public check of a printed extract. No login: this is what the QR code opens."""
    r = db.get(LandRecord, record_id)
    if r is None:
        return {"valid": False, "reason": "no such record"}
    current = fingerprint(r)
    if not hmac.compare_digest(current, fp.strip().lower()):
        return {"valid": False, "reason": "the record has changed since this extract was issued, or the extract is not genuine",
                "record_id": r.id}
    c = record_content(r)
    return {
        "valid": True,
        "record_id": r.id,
        "fingerprint_short": short(current),
        "location": {k: c[k] for k in ("village", "tehsil", "district", "state")},
        "khata_number": c["khata_number"],
        "khasra_numbers": [p.get("khasra_number") for p in (c["parcels"] or [])] or [c["khasra_number"]],
        "owners": [o.get("owner_name") for o in (c["owners"] or [])] or [c["owner_name"]],
        "verification": r.verification,
    }
