"""Admin: MIS statistics, audit trail, user management."""
from __future__ import annotations

import csv
import io
import json
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.extraction.confidence import default_threshold
from backend.extraction.extractor import extract
from backend.ocr.pipeline import run_ocr

from .. import audit
from ..auth import current_user, hash_password, require
from ..config import ALLOWED_EXTENSIONS, AUTO_ACCEPT_THRESHOLD, MAX_UPLOAD_MB, ROOT
from ..db import get_db
from ..models import AuditLog, Correction, Document, ExtractedField, LandRecord, User
from ..processing import get_memory
from ..schemas import UserCreate, UserOut, UserUpdate
from .documents import _check_decodable
from .integration import DISTRICT_HQ

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    by_status = dict(db.execute(select(Document.status, func.count()).group_by(Document.status)).all())
    total = sum(by_status.values())
    processed = sum(v for k, v in by_status.items() if k not in ("queued", "processing"))
    finished = by_status.get("auto_accepted", 0) + by_status.get("needs_review", 0) + by_status.get("verified", 0) \
        + by_status.get("rejected", 0)

    # accuracy measured from human review: fields confirmed as-is vs corrected
    reviewed = dict(db.execute(select(ExtractedField.status, func.count())
                               .where(ExtractedField.status.in_(("confirmed", "corrected", "rejected")))
                               .group_by(ExtractedField.status)).all())
    n_rev = sum(reviewed.values())
    per_field_rows = db.execute(select(ExtractedField.name, ExtractedField.status, func.count())
                                .where(ExtractedField.status.in_(("confirmed", "corrected", "rejected")))
                                .group_by(ExtractedField.name, ExtractedField.status)).all()
    per_field: dict[str, dict] = defaultdict(lambda: {"confirmed": 0, "corrected": 0, "rejected": 0})
    for name, st, n in per_field_rows:
        per_field[name][st] = n
    per_field_acc = {k: {**v, "accuracy": round(v["confirmed"] / max(1, sum(v.values())), 4)} for k, v in per_field.items()}

    # error statistics: issue types across all extracted fields + failed documents
    issue_counter: Counter = Counter()
    for (issues,) in db.execute(select(ExtractedField.issues)):
        for i in issues or []:
            issue_counter[i.split(":")[0].split("'")[0].strip()[:60]] += 1
    reason_counter: Counter = Counter()
    for (reasons,) in db.execute(select(Document.route_reasons).where(Document.route_reasons.is_not(None))):
        for r in reasons or []:
            reason_counter[r.split(":")[0]] += 1

    # geography
    geo = defaultdict(lambda: defaultdict(lambda: Counter()))
    for st, dist, status_, n in db.execute(select(Document.state, Document.district, Document.status, func.count())
                                           .group_by(Document.state, Document.district, Document.status)):
        geo[st or "Unknown"][dist or "Unknown"][status_] += n
    # district HQ coordinates (DISTRICT_HQ) let the dashboard plot a progress map alongside
    # the table; districts outside the 10-district master data just have no lat/lon
    geography = [{"state": st, "districts": [
                     {"district": d, "total": sum(c.values()), **c,
                      **({"lat": DISTRICT_HQ[d][0], "lon": DISTRICT_HQ[d][1]} if d in DISTRICT_HQ else {})}
                     for d, c in ds.items()],
                  "total": sum(sum(c.values()) for c in ds.values())} for st, ds in geo.items()]
    geography.sort(key=lambda g: -g["total"])

    # daily trend (last 14 days)
    since = datetime.now(timezone.utc) - timedelta(days=13)
    trend = Counter()
    auto_trend = Counter()
    for created, status_ in db.execute(select(Document.created_at, Document.status).where(Document.created_at >= since)):
        day = created.date().isoformat()
        trend[day] += 1
        if status_ == "auto_accepted":
            auto_trend[day] += 1
    days = [(since + timedelta(days=i)).date().isoformat() for i in range(14)]

    avg_conf = db.scalar(select(func.avg(Document.overall_confidence)).where(Document.overall_confidence.is_not(None)))
    avg_ms = db.scalar(select(func.avg(Document.processing_ms)).where(Document.processing_ms.is_not(None)))
    conf_hist = [0] * 10
    for (c,) in db.execute(select(Document.overall_confidence).where(Document.overall_confidence.is_not(None))):
        conf_hist[min(9, int(c * 10))] += 1

    eval_summary = None
    ev = ROOT / "eval" / "results" / "test.json"
    if ev.exists():
        eval_summary = json.loads(ev.read_text(encoding="utf-8"))["summary"]

    # What the repository holds: the kinds of record and the scripts they are written in.
    # Read from the documents themselves now, not from a land/non-land verdict.
    kinds: Counter = Counter()
    scripts: Counter = Counter()
    for kind, page_scripts in db.execute(select(Document.document_type, Document.scripts)):
        if kind:
            kinds[kind] += 1
        for name in page_scripts or []:
            scripts[name] += 1

    memory = get_memory(db)

    return {
        "repository": {
            "document_types": dict(kinds.most_common()),
            "scripts": dict(scripts.most_common()),
        },
        "totals": {
            "documents": total, "processed": processed, "by_status": by_status,
            "pending_verification": by_status.get("needs_review", 0),
            "auto_accept_rate": round(by_status.get("auto_accepted", 0) / finished, 4) if finished else None,
            "failed": by_status.get("failed", 0),
            "land_records": db.scalar(select(func.count(LandRecord.id))),
            "pushed_to_lrms": db.scalar(select(func.count(LandRecord.id)).where(LandRecord.lrms_ref.is_not(None))),
        },
        "accuracy": {
            "reviewed_fields": n_rev,
            "field_accuracy": round(reviewed.get("confirmed", 0) / n_rev, 4) if n_rev else None,
            "corrected": reviewed.get("corrected", 0), "rejected": reviewed.get("rejected", 0),
            "per_field": per_field_acc,
            "benchmark": eval_summary,
        },
        "confidence": {"average": round(avg_conf, 4) if avg_conf is not None else None, "histogram": conf_hist,
                       "threshold": AUTO_ACCEPT_THRESHOLD or default_threshold()},
        "processing": {"avg_seconds": round(avg_ms / 1000, 2) if avg_ms else None},
        "errors": {"issues": issue_counter.most_common(10), "review_reasons": reason_counter.most_common(10)},
        "geography": geography,
        "trend": [{"day": d, "uploaded": trend.get(d, 0), "auto_accepted": auto_trend.get(d, 0)} for d in days],
        "learning": {"corrections": db.scalar(select(func.count(Correction.id))),
                     "learned_patterns": len(memory.subs),
                     "adapted_thresholds": memory.field_thresholds(AUTO_ACCEPT_THRESHOLD)},
    }


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    """Has anything in the audit trail been altered since it was written?

    Each entry is hashed together with the one before it, so an edit or a deletion shows up
    here as the first entry that stops matching. See backend/api/audit.py for what this does
    and does not promise."""
    return audit.verify_chain(db)


@router.get("/audit")
def audit_log(entity_type: str | None = None, entity_id: int | None = None, action: str | None = None,
              username: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(AuditLog)
    if user.role != "admin":
        # non-admins may only read the trail of a specific document
        if entity_type != "document" or entity_id is None:
            raise HTTPException(403, "only admins can browse the full audit log")
        # ...and only of a document they are allowed to open. Without this an operator could
        # walk document ids and read who reviewed what, with the reviewers' IP addresses.
        # A document that does not exist simply yields an empty trail, which tells the caller
        # nothing about which ids are real.
        if user.role == "operator":
            doc = db.get(Document, entity_id)
            if doc is not None and doc.uploaded_by != user.id:
                raise HTTPException(403, "operators can only see the audit trail of their own documents")
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    if username:  # "who did this?" — the trail keeps the username as it was at the time
        stmt = stmt.where(AuditLog.username == username)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.ts.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"total": total, "items": [
        {"id": r.id, "ts": r.ts.isoformat(), "user": r.username, "action": r.action, "entity_type": r.entity_type,
         "entity_id": r.entity_id, "details": {k: v for k, v in (r.details or {}).items() if k != "trace"}, "ip": r.ip}
        for r in rows]}


class UserRow(UserOut):
    last_login: str | None = None  # most recent successful sign-in, from the audit trail


@router.get("/users", response_model=list[UserRow])
def list_users(db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    """Accounts, with when each was last used (an unused account is worth asking about)."""
    seen = dict(db.execute(select(AuditLog.username, func.max(AuditLog.ts))
                           .where(AuditLog.action == "auth.login").group_by(AuditLog.username)).all())
    rows = []
    for u in db.scalars(select(User).order_by(User.id)):
        row = UserRow.model_validate(u)
        ts = seen.get(u.username)
        row.last_login = ts.isoformat() if ts else None
        rows.append(row)
    return rows


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "username taken")
    u = User(username=body.username, full_name=body.full_name, role=body.role, password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    audit.log(db, "user.created", user, "user", u.id, {"username": u.username, "role": u.role}, request)
    db.commit()
    return u


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require("admin"))):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "user not found")
    changes = body.model_dump(exclude_none=True)
    if u.id == user.id and (changes.get("active") is False or changes.get("role", "admin") != "admin"):
        raise HTTPException(400, "you cannot demote or deactivate yourself")
    if "password" in changes:
        u.password_hash = hash_password(changes.pop("password"))
        changes["password"] = "changed"
    for k, v in changes.items():
        if k != "password":
            setattr(u, k, v)
    audit.log(db, "user.updated", user, "user", u.id, changes, request)
    db.commit()
    return u


_RECORD_COLUMNS = ["id", "state", "district", "tehsil", "village", "khata_number", "khasra_number",
                   "survey_number", "owner_name", "father_name", "plot_area", "area_hectares",
                   "land_classification", "mutation_number", "mutation_date", "lrms_ref", "verification"]


@router.get("/export/records.csv")
def export_records_csv(district: str | None = None, state: str | None = None,
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Verified land records as CSV - a flat, tool-agnostic feed any BI/reporting tool
    (Power BI, Superset, Grafana, Excel) can import or poll, without a bespoke connector."""
    stmt = select(LandRecord)
    if district:
        stmt = stmt.where(LandRecord.district == district)
    if state:
        stmt = stmt.where(LandRecord.state == state)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_RECORD_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in db.scalars(stmt.order_by(LandRecord.id)):
        writer.writerow({c: getattr(r, c, None) for c in _RECORD_COLUMNS})
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=land_records.csv"})


@router.get("/export/stats.csv")
def export_stats_csv(db: Session = Depends(get_db), user: User = Depends(require("verifier"))):
    """Per-district digitization progress as CSV, for the same BI tools."""
    rows = db.execute(select(Document.state, Document.district, Document.status, func.count())
                      .group_by(Document.state, Document.district, Document.status)).all()
    tree: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for st, dist, status_, n in rows:
        tree[(st or "Unknown", dist or "Unknown")][status_] = n
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["state", "district", "documents_received", "digitized", "pending_verification", "progress_pct"])
    for (st, dist), counts in sorted(tree.items()):
        total = sum(counts.values())
        digitized = counts.get("verified", 0) + counts.get("auto_accepted", 0)
        pending = counts.get("needs_review", 0)
        pct = round(100 * digitized / total, 1) if total else 0
        writer.writerow([st, dist, total, digitized, pending, pct])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=district_progress.csv"})


REAL_DIR = ROOT / "data" / "real"


def _compare_to_ground_truth(extraction: dict, gt_fields: dict) -> list[dict]:
    """Per-field extracted-vs-correct, using the exact comparison eval/evaluate.py scores
    a whole split with (field_correct) - so a single interactive check and the aggregate
    report never quietly disagree about what "correct" means."""
    from eval.evaluate import field_correct

    out = []
    for name, gt_value in gt_fields.items():
        pred = extraction["fields"].get(name)
        out.append({"field": name, "ground_truth": gt_value,
                    "extracted": pred["value"] if pred else None,
                    "confidence": pred["confidence"] if pred else None,
                    "correct": field_correct(name, pred, gt_value)})
    return out


@router.post("/real-samples")
async def add_real_sample(request: Request, file: UploadFile = File(...), ground_truth: str = Form(...),
                          db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    """Upload a real land record plus its correct field values, typed by a person reading
    it, and see the pipeline's accuracy on it immediately. Saved into data/real/ in the
    exact shape `eval/evaluate.py --split real` expects (data/real/README.md), so every
    sample added here also counts toward that aggregate report later - this is the same
    workflow, just interactive instead of a shell script."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"file larger than {MAX_UPLOAD_MB} MB")
    _check_decodable(data, ext)
    try:
        gt = json.loads(ground_truth)
    except json.JSONDecodeError:
        raise HTTPException(400, "ground_truth is not valid JSON")
    gt_fields = gt.get("fields") or {}
    if not gt_fields:
        raise HTTPException(400, "ground_truth needs at least one field under 'fields'")

    sample_id = f"web-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(3)}"
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    (REAL_DIR / f"{sample_id}{ext}").write_bytes(data)
    (REAL_DIR / f"{sample_id}.json").write_text(json.dumps({"fields": gt_fields}, ensure_ascii=False, indent=1),
                                                encoding="utf-8")

    extraction = extract(run_ocr(data, file.filename or ""))
    comparison = _compare_to_ground_truth(extraction, gt_fields)
    field_accuracy = round(sum(1 for c in comparison if c["correct"]) / len(comparison), 4) if comparison else None

    audit.log(db, "real_sample.added", user, "real_sample", None,
              {"sample_id": sample_id, "filename": file.filename, "field_accuracy": field_accuracy}, request)
    db.commit()
    return {"sample_id": sample_id, "document_type": extraction["document_type"],
            "overall_confidence": extraction["overall_confidence"], "route": extraction["route"],
            "field_accuracy": field_accuracy, "fields": comparison}


@router.get("/real-samples")
def list_real_samples(user: User = Depends(require("admin"))):
    """Samples measured so far, newest first - visible without a shell, matching what
    `python eval/evaluate.py --split real` would pick up from data/real/."""
    if not REAL_DIR.exists():
        return []
    out = []
    for p in sorted(REAL_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        has_file = any(p.with_suffix(e).exists() for e in ALLOWED_EXTENSIONS)
        out.append({"sample_id": p.stem, "fields": sorted((meta.get("fields") or {}).keys()), "has_file": has_file,
                    "added": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()})
    return out
