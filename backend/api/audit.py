from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog, User


def log(db: Session, action: str, user: User | None = None, entity_type: str | None = None,
        entity_id: int | None = None, details: dict | None = None, request: Request | None = None) -> None:
    """Append an audit entry. Caller commits."""
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action, entity_type=entity_type, entity_id=entity_id, details=details,
        ip=request.client.host if request and request.client else None,
    ))
