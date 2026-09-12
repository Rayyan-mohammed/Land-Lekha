"""Admin: MIS statistics, audit trail, user management."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.extraction.confidence import default_threshold

from .. import audit
from ..auth import current_user, hash_password, require
from ..config import AUTO_ACCEPT_THRESHOLD, ROOT
from ..db import get_db
from ..models import AuditLog, Correction, Document, ExtractedField, LandRecord, User
from ..processing import get_memory
from ..schemas import UserCreate, UserOut, UserUpdate

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
    geography = [{"state": st, "districts": [{"district": d, "total": sum(c.values()), **c} for d, c in ds.items()],
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

    memory = get_memory(db)
    return {
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


@router.get("/audit")
def audit_log(entity_type: str | None = None, entity_id: int | None = None, action: str | None = None,
              username: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(AuditLog)
    if user.role != "admin":
        # non-admins may only read the trail of a specific document
        if entity_type != "document" or entity_id is None:
            raise HTTPException(403, "only admins can browse the full audit log")
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
