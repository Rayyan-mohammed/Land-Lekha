"""Database schema.

documents        one uploaded file and its processing state
extracted_fields one row per field per document (value, confidence, review status)
land_records     the verified, canonical record (what gets pushed to LRMS)
corrections      verifier corrections (feeds the learning memory)
audit_log        every state-changing action, who did it and when
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))  # operator | verifier | admin
    password_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # queued | processing | auto_accepted | needs_review | verified | rejected | failed
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    document_type: Mapped[str | None] = mapped_column(String(32))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    ocr: Mapped[dict | None] = mapped_column(JSON)
    extraction: Mapped[dict | None] = mapped_column(JSON)
    overall_confidence: Mapped[float | None] = mapped_column(Float)
    route_reasons: Mapped[list | None] = mapped_column(JSON)
    owners: Mapped[list | None] = mapped_column(JSON)  # co-owners under one khata, see docs/contracts.md
    parcels: Mapped[list | None] = mapped_column(JSON)  # khasra/area/class rows under one khata
    # set when a worker claims the document (claim_document); tells a restarting replica
    # whether "processing" here means another live replica is mid-flight, or genuinely crashed
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(64), index=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fields: Mapped[list[ExtractedField]] = relationship(back_populates="document", cascade="all, delete-orphan",
                                                        order_by="ExtractedField.id")
    uploader: Mapped[User] = relationship(foreign_keys=[uploaded_by])


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (UniqueConstraint("document_id", "name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(32))
    value: Mapped[str | None] = mapped_column(Text)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
    issues: Mapped[list | None] = mapped_column(JSON)
    page: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(16))
    # auto | pending | confirmed | corrected | rejected
    status: Mapped[str] = mapped_column(String(16), default="pending")
    original_value: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="fields")


class LandRecord(Base):
    __tablename__ = "land_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), unique=True)
    owner_name: Mapped[str | None] = mapped_column(String(128), index=True)
    father_name: Mapped[str | None] = mapped_column(String(128))
    khata_number: Mapped[str | None] = mapped_column(String(32), index=True)
    khasra_number: Mapped[str | None] = mapped_column(String(32), index=True)
    survey_number: Mapped[str | None] = mapped_column(String(32))
    plot_area: Mapped[str | None] = mapped_column(String(32))
    area_hectares: Mapped[float | None] = mapped_column(Float)
    land_classification: Mapped[str | None] = mapped_column(String(32))
    owners: Mapped[list | None] = mapped_column(JSON)
    parcels: Mapped[list | None] = mapped_column(JSON)
    village: Mapped[str | None] = mapped_column(String(64), index=True)
    tehsil: Mapped[str | None] = mapped_column(String(64))
    district: Mapped[str | None] = mapped_column(String(64), index=True)
    state: Mapped[str | None] = mapped_column(String(64), index=True)
    mutation_number: Mapped[str | None] = mapped_column(String(32))
    mutation_date: Mapped[str | None] = mapped_column(String(16))
    registration_number: Mapped[str | None] = mapped_column(String(32))
    registration_date: Mapped[str | None] = mapped_column(String(16))
    verification: Mapped[str] = mapped_column(String(16))  # auto | human
    lrms_ref: Mapped[str | None] = mapped_column(String(64))
    lrms_pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(String(32), index=True)
    raw_value: Mapped[str | None] = mapped_column(Text)
    extracted_value: Mapped[str | None] = mapped_column(Text)
    corrected_value: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(48), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(32))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))
    # Tamper-evidence: each row carries a hash of its own contents chained to the row before it,
    # so an entry that is edited or removed later stops matching (see backend/api/audit.py).
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str | None] = mapped_column(String(64), index=True)


class LoginAttempt(Base):
    """Login brute-force throttling state, one row per (ip, username) - see ratelimit.py.
    A database table rather than an in-memory dict so the lockout is shared across every
    replica behind a load balancer (docker-compose --scale api=N), not just the one that
    happened to see a given request."""
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)  # "ip:username"
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
