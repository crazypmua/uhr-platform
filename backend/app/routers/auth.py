from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import (
    clear_session_cookie,
    create_token,
    exchange_preview_token,
    get_current_admin,
    set_session_cookie,
    set_preview_cookie,
    verify_password,
)
from ..db import get_db
from ..models import User
from ..schemas import LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Невірний email або пароль")
    set_session_cookie(response, create_token(user))
    return {"ok": True, "email": user.email, "name": user.name, "role": user.role}


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_admin)):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.get("/preview")
def preview_exchange(token: str, request: Request):
    host = (request.headers.get("host") or "").split(":")[0].lower()
    site = "ukrwerkspot" if "ukrwerkspot" in host else "uhrbv"
    preview_cookie = exchange_preview_token(token, site)
    response = RedirectResponse("/", status_code=302)
    set_preview_cookie(response, preview_cookie)
    return response
