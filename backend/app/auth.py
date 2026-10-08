from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

TOKEN_HOURS = 72
PREVIEW_TOKEN_MINUTES = 5
PREVIEW_COOKIE_HOURS = 1


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_preview_token(site: str, user: User) -> str:
    payload = {
        "sub": str(user.id),
        "site": site,
        "purpose": "site_preview_exchange",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=PREVIEW_TOKEN_MINUTES),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def exchange_preview_token(token: str, site: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Посилання для перегляду недійсне") from exc
    if payload.get("purpose") != "site_preview_exchange" or payload.get("site") != site:
        raise HTTPException(status_code=401, detail="Посилання призначене для іншого сайту")
    preview_payload = {
        "site": site,
        "purpose": "site_preview",
        "exp": datetime.now(timezone.utc) + timedelta(hours=PREVIEW_COOKIE_HOURS),
    }
    return jwt.encode(preview_payload, settings.secret_key, algorithm="HS256")


def has_preview_access(request: Request, site: str) -> bool:
    token = request.cookies.get(settings.preview_cookie_name)
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    return payload.get("purpose") == "site_preview" and payload.get("site") == site


def has_admin_session(request: Request) -> bool:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    return payload.get("role") == "admin"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=TOKEN_HOURS * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie(settings.preview_cookie_name, path="/")


def set_preview_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.preview_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=PREVIEW_COOKIE_HOURS * 3600,
        path="/",
    )


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Потрібна авторизація")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Сесію закінчено")
    user = db.get(User, user_id)
    if not user or not user.is_active or user.role != "admin":
        raise HTTPException(status_code=401, detail="Немає доступу")
    return user
