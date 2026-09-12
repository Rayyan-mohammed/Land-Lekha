from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit, ratelimit
from ..auth import create_token, current_user, verify_password
from ..db import get_db
from ..models import User
from ..schemas import TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    locked_for = ratelimit.check(ip, form.username)
    if locked_for is not None:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"too many failed attempts, try again in {int(locked_for) + 1}s")
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not user.active or not verify_password(form.password, user.password_hash):
        ratelimit.record_failure(ip, form.username)
        audit.log(db, "auth.login_failed", None, "user", None, {"username": form.username}, request)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong username or password")
    ratelimit.record_success(ip, form.username)
    audit.log(db, "auth.login", user, "user", user.id, None, request)
    db.commit()
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
