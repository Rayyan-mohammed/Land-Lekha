from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str
    active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=128)
    role: Literal["operator", "verifier", "admin"]
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Literal["operator", "verifier", "admin"] | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    value: str | None
    raw_value: str | None
    normalized: dict | None
    confidence: float
    ocr_confidence: float | None
    valid: bool
    issues: list | None
    page: int | None
    bbox: list | None
    source: str | None
    status: str
    original_value: str | None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    status: str
    document_type: str | None
    overall_confidence: float | None
    state: str | None
    district: str | None
    page_count: int
    processing_ms: int | None
    uploaded_by: int
    created_at: datetime
    processed_at: datetime | None


class DocumentDetail(DocumentSummary):
    fields: list[FieldOut]
    route_reasons: list | None
    error: str | None
    review_note: str | None
    reviewed_at: datetime | None
    consistency: list = []
    duplicates: list = []
    pages: list[dict] = []
    uploader_name: str | None = None
    record_id: int | None = None
    threshold: float | None = None
    owners: list | None = None
    parcels: list | None = None


class FieldDecision(BaseModel):
    action: Literal["confirm", "correct", "reject"]
    value: str | None = None


class VerifyIn(BaseModel):
    decision: Literal["approve", "reject"]
    fields: dict[str, FieldDecision] = {}
    note: str | None = Field(default=None, max_length=2000)


class DisputeIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


TokenOut.model_rebuild()
