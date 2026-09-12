"""GraphQL surface over the same verified data as the REST `/api/integration` routes.

PS 26018 lists RESTful/GraphQL APIs as acceptable integration surfaces; the REST routes
in `routes/integration.py` were the only option before this. This is read-only by design:
mutations (verify, push to LRMS) stay REST-only where the audit trail and validation
logic already live, so this file is a second view onto the same data, not a second
place logic can drift.

Auth reuses the existing JWT bearer scheme: a `Authorization: Bearer <token>` header is
required exactly as for REST, checked once in `get_context` before any resolver runs.
"""
from __future__ import annotations

import strawberry
from fastapi import HTTPException, Request
from strawberry.fastapi import GraphQLRouter

from .auth import ALGO
from .config import JWT_SECRET
from .db import SessionLocal
from .models import Document, LandRecord, User
from .routes.integration import _lrms_record

import jwt as pyjwt
from sqlalchemy import func, select


@strawberry.type
class Owner:
    name: str | None
    father_or_husband: str | None


@strawberry.type
class Parcel:
    khasra_no: str | None
    area: float | None
    land_class: str | None


@strawberry.type
class LandRecordType:
    record_id: int
    state: str | None
    district: str | None
    tehsil: str | None
    village: str | None
    khata_no: str | None
    owners: list[Owner]
    parcels: list[Parcel]
    lrms_ref: str | None

    @staticmethod
    def from_dict(d: dict) -> "LandRecordType":
        loc = d["location"]
        return LandRecordType(
            record_id=d["record_id"], state=loc.get("state"), district=loc.get("district"),
            tehsil=loc.get("tehsil"), village=loc.get("village"), khata_no=d["account"]["khata_no"],
            owners=[Owner(name=o.get("name"), father_or_husband=o.get("father_or_husband"))
                   for o in d["account"]["owners"]],
            parcels=[Parcel(khasra_no=p.get("khasra_no"), area=p.get("area"), land_class=p.get("land_class"))
                    for p in d["parcels"]],
            lrms_ref=d.get("lrms_ref"),
        )


@strawberry.type
class DistrictProgress:
    district: str
    documents_received: int
    digitized: int
    pending_verification: int
    progress_pct: float


@strawberry.type
class Query:
    @strawberry.field
    def land_records(self, info: strawberry.Info, district: str | None = None, village: str | None = None,
                     khata: str | None = None, limit: int = 100) -> list[LandRecordType]:
        db = info.context["db"]
        stmt = select(LandRecord)
        for col, val in ((LandRecord.district, district), (LandRecord.village, village),
                         (LandRecord.khata_number, khata)):
            if val:
                stmt = stmt.where(col == val)
        rows = db.scalars(stmt.order_by(LandRecord.id.desc()).limit(max(0, min(limit, 500))))
        return [LandRecordType.from_dict(_lrms_record(r)) for r in rows]

    @strawberry.field
    def land_record(self, info: strawberry.Info, record_id: int) -> LandRecordType | None:
        db = info.context["db"]
        r = db.get(LandRecord, record_id)
        return LandRecordType.from_dict(_lrms_record(r)) if r else None

    @strawberry.field
    def dilrmp_progress(self, info: strawberry.Info) -> list[DistrictProgress]:
        db = info.context["db"]
        rows = db.execute(select(Document.district, Document.status, func.count())
                          .group_by(Document.district, Document.status)).all()
        tree: dict[str, dict[str, int]] = {}
        for dist, status_, n in rows:
            tree.setdefault(dist or "Unknown", {})[status_] = n
        out = []
        for dist, counts in sorted(tree.items()):
            total = sum(counts.values())
            digitized = counts.get("verified", 0) + counts.get("auto_accepted", 0)
            out.append(DistrictProgress(district=dist, documents_received=total, digitized=digitized,
                                        pending_verification=counts.get("needs_review", 0),
                                        progress_pct=round(100 * digitized / total, 1) if total else 0.0))
        return out


schema = strawberry.Schema(query=Query)


async def get_context(request: Request) -> dict:
    """Same bearer-token check as REST `current_user`, adapted for GraphQL's single
    context hook instead of FastAPI's per-route `Depends`."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except pyjwt.PyJWTError:
        raise HTTPException(401, "invalid or expired token")
    db = SessionLocal()
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.active:
        db.close()
        raise HTTPException(401, "invalid or expired token")
    # Every query here reads verified land records, which carry owner names. That is the same
    # data REST serves from /api/integration/lrms/*, and it is gated the same way: an operator
    # uploads pages and sees their own uploads, and does not get the register through GraphQL.
    if user.role not in ("verifier", "admin"):
        db.close()
        raise HTTPException(403, "requires role: verifier")
    return {"db": db, "user": user}


graphql_router = GraphQLRouter(schema, path="/api/graphql", context_getter=get_context)
