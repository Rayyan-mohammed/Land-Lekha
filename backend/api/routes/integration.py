"""Integration APIs for LRMS, DILRMP and GIS.

These are real, documented endpoints over our own verified data. The *external*
government systems are not reachable from this prototype, so pushes return a
simulated acknowledgement (clearly marked `"mock": true`) and GIS geometry is a
synthetic parcel placed near the district headquarters.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..auth import current_user, require
from ..db import get_db
from ..models import Document, LandRecord, User, utcnow

router = APIRouter(prefix="/api/integration", tags=["integration (mock external systems)"])

DISTRICT_HQ = {
    "Lucknow": (26.8467, 80.9462), "Barabanki": (26.9268, 81.1834), "Varanasi": (25.3176, 82.9739),
    "Agra": (27.1767, 78.0081), "Bhopal": (23.2599, 77.4126), "Sehore": (23.2032, 77.0844),
    "Jaipur": (26.9124, 75.7873), "Ajmer": (26.4499, 74.6399), "Patna": (25.5941, 85.1376), "Gaya": (24.7914, 85.0002),
}


def _lrms_record(r: LandRecord) -> dict:
    """Record in an LRMS-style exchange format. `parcel` (singular) is the first khasra
    row, kept for existing consumers; `parcels` lists every row under this khata."""
    owners = r.owners or [{"owner_name": r.owner_name, "father_name": r.father_name}]
    parcels = r.parcels or [{"khasra_number": r.khasra_number, "plot_area": r.plot_area,
                             "land_classification": r.land_classification}]
    return {
        "record_id": r.id,
        "location": {"state": r.state, "district": r.district, "tehsil": r.tehsil, "village": r.village},
        "account": {"khata_no": r.khata_number,
                    "owners": [{"name": o.get("owner_name"), "father_or_husband": o.get("father_name")} for o in owners]},
        "parcel": {"khasra_no": r.khasra_number, "survey_no": r.survey_number, "area": r.plot_area,
                   "area_hectares": r.area_hectares, "land_class": r.land_classification},
        "parcels": [{"khasra_no": p.get("khasra_number"), "area": p.get("plot_area"),
                    "land_class": p.get("land_classification")} for p in parcels],
        "mutation": {"number": r.mutation_number, "date": r.mutation_date} if r.mutation_number else None,
        "registration": {"number": r.registration_number, "date": r.registration_date} if r.registration_number else None,
        "provenance": {"source_document_id": r.document_id, "verification": r.verification,
                       "digitized_at": r.created_at.isoformat() if r.created_at else None},
        "lrms_ref": r.lrms_ref,
    }


# Verified records hold owner and father names, khata and khasra numbers. An operator
# uploads pages and sees their own uploads (routes/documents.py); they have no business
# reading the whole register, so every record read here is verifier-and-above.
@router.get("/lrms/records")
def lrms_records(district: str | None = None, village: str | None = None, khata: str | None = None,
                 khasra: str | None = None, limit: int = 100, db: Session = Depends(get_db),
                 user: User = Depends(require("verifier"))):
    """Query verified records in LRMS exchange format."""
    stmt = select(LandRecord)
    for col, val in ((LandRecord.district, district), (LandRecord.village, village),
                     (LandRecord.khata_number, khata), (LandRecord.khasra_number, khasra)):
        if val:
            stmt = stmt.where(col == val)
    rows = list(db.scalars(stmt.order_by(LandRecord.id.desc()).limit(max(0, min(limit, 500)))))
    return {"count": len(rows), "records": [_lrms_record(r) for r in rows]}


@router.get("/lrms/records/{record_id}")
def lrms_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    r = db.get(LandRecord, record_id)
    if r is None:
        raise HTTPException(404, "record not found")
    return _lrms_record(r)


@router.post("/lrms/push/{record_id}")
def lrms_push(record_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """Push a verified record to the state LRMS (simulated acknowledgement)."""
    r = db.get(LandRecord, record_id)
    if r is None:
        raise HTTPException(404, "record not found")
    if not r.lrms_ref:
        code = {"Uttar Pradesh": "UP", "Madhya Pradesh": "MP", "Rajasthan": "RJ", "Bihar": "BR"}.get(r.state or "", "XX")
        r.lrms_ref = f"LRMS-{code}-{utcnow():%Y}-{r.id:06d}"
        r.lrms_pushed_at = utcnow()
        audit.log(db, "integration.lrms_push", user, "land_record", r.id, {"lrms_ref": r.lrms_ref}, request)
        db.commit()
    return {"mock": True, "status": "accepted", "lrms_ref": r.lrms_ref,
            "pushed_at": r.lrms_pushed_at.isoformat() if r.lrms_pushed_at else None, "payload": _lrms_record(r)}


@router.get("/register/check/{doc_id}")
def register_check(doc_id: int, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """Compare what we read off this document with what the state register holds.

    Simulated: there is no state API to call, so the register is a local table (see
    backend/integration/register.py). A match here is **not** evidence that a document is
    genuine - it means the two records say the same thing. Every response carries
    `"simulated": true` and the UI says so."""
    from backend.integration.register import Register, compare

    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    if user.role == "operator" and doc.uploaded_by != user.id:
        raise HTTPException(403, "operators can only see their own uploads")
    mine = {f.name: f.value for f in doc.fields if f.value and f.status != "rejected"}
    register = Register.load()
    result = compare(mine, register.find(mine))
    result["document_id"] = doc.id
    result["register_size"] = len(register.entries)
    return result


@router.get("/dilrmp/progress")
def dilrmp_progress(db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """DILRMP-style MIS progress report: digitization status by state and district."""
    rows = db.execute(select(Document.state, Document.district, Document.status, func.count())
                      .group_by(Document.state, Document.district, Document.status)).all()
    tree: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for st, dist, status_, n in rows:
        tree[st or "Unknown"][dist or "Unknown"][status_] += n
    report = []
    for st, dists in sorted(tree.items()):
        drows = []
        for dist, c in sorted(dists.items()):
            total = sum(c.values())
            digitized = c.get("verified", 0) + c.get("auto_accepted", 0)
            drows.append({"district": dist, "documents_received": total, "digitized": digitized,
                          "pending_verification": c.get("needs_review", 0), "rejected": c.get("rejected", 0),
                          "failed": c.get("failed", 0), "progress_pct": round(100 * digitized / total, 1) if total else 0})
        tot = sum(d["documents_received"] for d in drows)
        dig = sum(d["digitized"] for d in drows)
        report.append({"state": st, "documents_received": tot, "digitized": dig,
                       "progress_pct": round(100 * dig / tot, 1) if tot else 0, "districts": drows})
    return {"mock": True, "programme": "DILRMP", "component": "Computerization of Land Records",
            "generated_at": utcnow().isoformat(), "states": report}


def _parcel_polygon(r: LandRecord) -> list[list[float]]:
    lat0, lon0 = DISTRICT_HQ.get(r.district or "", (23.5, 80.0))
    h = hashlib.sha256(f"{r.village}|{r.khasra_number}".encode()).digest()
    # deterministic offset up to ~15 km from HQ
    dlat = (h[0] / 255 - 0.5) * 0.27
    dlon = (h[1] / 255 - 0.5) * 0.27
    side_m = math.sqrt(max(r.area_hectares or 0.2, 0.01) * 10000)
    dy = side_m / 111_320
    dx = side_m / (111_320 * math.cos(math.radians(lat0 + dlat)))
    lat, lon = lat0 + dlat, lon0 + dlon
    skew = (h[2] / 255 - 0.5) * 0.3
    return [[lon, lat], [lon + dx, lat + dy * skew * 0.2], [lon + dx * (1 + skew * 0.2), lat + dy],
            [lon + dx * skew * 0.2, lat + dy], [lon, lat]]


def _feature(r: LandRecord) -> dict:
    return {"type": "Feature", "id": r.id,
            "geometry": {"type": "Polygon", "coordinates": [_parcel_polygon(r)]},
            "properties": {"record_id": r.id, "khasra_no": r.khasra_number, "khata_no": r.khata_number,
                           "owner": r.owner_name, "village": r.village, "district": r.district,
                           "area_hectares": r.area_hectares, "land_class": r.land_classification,
                           "synthetic_geometry": True}}


@router.get("/gis/parcels")
def gis_parcels(district: str | None = None, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """GeoJSON FeatureCollection of digitized parcels (synthetic geometry)."""
    stmt = select(LandRecord)
    if district:
        stmt = stmt.where(LandRecord.district == district)
    feats = [_feature(r) for r in db.scalars(stmt.limit(1000))]
    return {"type": "FeatureCollection", "mock": True, "features": feats}


@router.get("/gis/parcels/{record_id}")
def gis_parcel(record_id: int, db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    r = db.get(LandRecord, record_id)
    if r is None:
        raise HTTPException(404, "record not found")
    return _feature(r)
