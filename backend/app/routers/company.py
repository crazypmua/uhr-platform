import asyncio
import json
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from ..auth import (
    clear_company_cookie,
    get_company_account,
    hash_password,
    set_company_cookie,
    verify_password,
)
from ..config import settings
from ..db import get_db
from ..documents import kind_label, read_uploads
from ..inbox import close as close_inbox
from ..inbox import listen as listen_inbox
from ..inbox import publish
from ..mailer import send_mail
from ..models import (
    Company,
    CompanyAccount,
    CompanyFavorite,
    CompanyPick,
    Craftsman,
    Document,
    Message,
    Request as WorkRequest,
    RequestSelection,
)
from ..notifications import company_password_reset
from ..schemas import (
    CompanyMessageIn,
    CompanyProfileUpdate,
    CompanyRegistration,
    CompanyRequestIn,
    CompanySignup,
    SelectionContactIn,
    EmailIn,
    LoginIn,
    PasswordResetIn,
)
from ..sna import check_certificate
from .public import _save_with_documents, _validation_detail

router = APIRouter(prefix="/company", tags=["company"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
OAUTH_COOKIE = "uhr_oauth_state"
RESET_LINK = "Deze herstellink is ongeldig of verlopen. Vraag een nieuwe aan."
REQUEST_LABELS = {
    "draft": "Concept",
    "submitted": "Ingediend",
    "in_progress": "In behandeling",
    "candidate": "Kandidaat geselecteerd",
    "confirmed": "Bevestigd",
    "done": "Afgerond",
    "cancelled": "Geannuleerd",
}


def _account_out(account: CompanyAccount) -> dict:
    company = account.company
    return {
        "email": account.email,
        "google": bool(account.google_sub),
        "company": {
            "id": company.id,
            "status": company.status,
            "company_name": company.company_name,
            "admin_comment": company.admin_comment if company.status in {"clarification", "rejected"} else "",
        } if company else None,
    }


def _login(response: Response, account: CompanyAccount, db: Session) -> dict:
    account.last_login_at = datetime.now(timezone.utc)
    db.commit()
    set_company_cookie(response, account)
    return _account_out(account)


@router.get("/auth/config")
def auth_config():
    return {"google": settings.google_enabled}


@router.get("/me")
def me(account: CompanyAccount = Depends(get_company_account)):
    return _account_out(account)


@router.post("/auth/register")
def register(payload: CompanySignup, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(CompanyAccount).filter(CompanyAccount.email == email).first():
        raise HTTPException(status_code=409, detail="Er bestaat al een account met dit e-mailadres. Log in.")
    account = CompanyAccount(email=email, password_hash=hash_password(payload.password))
    db.add(account)
    db.flush()
    return _login(response, account, db)


@router.post("/auth/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    account = db.query(CompanyAccount).filter(CompanyAccount.email == payload.email.lower()).first()
    if not account or not account.password_hash or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Onjuist e-mailadres of wachtwoord")
    return _login(response, account, db)


@router.post("/auth/logout")
def logout(response: Response):
    clear_company_cookie(response)
    return {"ok": True}


def _reset_token(account: CompanyAccount) -> str:
    payload = {
        "sub": str(account.id),
        "purpose": "company_reset",
        # Ties the link to the current password, so a used link stops working
        "pw": account.password_hash[-12:] if account.password_hash else "",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _account_from_reset(token: str, db: Session) -> CompanyAccount:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        account_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail=RESET_LINK)
    current = ""
    account = db.get(CompanyAccount, account_id) if payload.get("purpose") == "company_reset" else None
    if account and account.password_hash:
        current = account.password_hash[-12:]
    if not account or payload.get("pw") != current:
        raise HTTPException(status_code=400, detail=RESET_LINK)
    return account


@router.post("/auth/forgot")
def forgot(payload: EmailIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    account = db.query(CompanyAccount).filter(CompanyAccount.email == payload.email.lower()).first()
    if account:
        link = f"{settings.uhrbv_url.rstrip('/')}/#reset/{_reset_token(account)}"
        background.add_task(send_mail, account.email, *company_password_reset(link))
    return {"ok": True}


@router.post("/auth/reset")
def reset_password(payload: PasswordResetIn, response: Response, db: Session = Depends(get_db)):
    account = _account_from_reset(payload.token, db)
    account.password_hash = hash_password(payload.password)
    return _login(response, account, db)


@router.get("/auth/google/start")
def google_start():
    if not settings.google_enabled:
        raise HTTPException(status_code=404, detail="Inloggen met Google is niet ingesteld")
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    })
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}", status_code=302)
    response.set_cookie(OAUTH_COOKIE, state, max_age=600, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", path="/api/v1/company/auth/google")
    return response


def _google_identity(code: str) -> dict:
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(GOOGLE_TOKEN_URL, data=body), timeout=10) as response:
        tokens = json.loads(response.read())
    # The token comes straight from Google over TLS, so its claims are trusted without checking the signature
    claims = jwt.decode(tokens["id_token"], options={"verify_signature": False})
    if claims.get("aud") != settings.google_client_id or claims.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("id_token is not issued for this client")
    if not claims.get("email_verified"):
        raise ValueError("Google e-mail is not verified")
    return claims


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)):
    expected = request.cookies.get(OAUTH_COOKIE)
    if not code or not expected or not secrets.compare_digest(expected, state):
        return RedirectResponse("/#login", status_code=302)
    try:
        claims = _google_identity(code)
    except Exception:
        return RedirectResponse("/#login", status_code=302)
    email = claims["email"].lower()
    account = db.query(CompanyAccount).filter(CompanyAccount.google_sub == claims["sub"]).first()
    if not account:
        account = db.query(CompanyAccount).filter(CompanyAccount.email == email).first()
        if account:
            account.google_sub = claims["sub"]
        else:
            account = CompanyAccount(email=email, google_sub=claims["sub"])
            db.add(account)
        db.flush()
    target = "overview" if account.company and account.company.status == "approved" else "register"
    response = RedirectResponse(f"/#{target}", status_code=302)
    response.delete_cookie(OAUTH_COOKIE, path="/api/v1/company/auth/google")
    _login(response, account, db)
    return response


async def _read_certificate(file: UploadFile, kind: str) -> tuple[str, str, bytes]:
    uploads = await read_uploads({kind: [file]}, "company")
    if not uploads.get(kind):
        detail = "Voeg het ISO 9001-certificaat toe" if kind == "iso" else "Voeg het SNA-certificaat toe"
        raise HTTPException(status_code=422, detail=detail)
    return uploads[kind][0]


@router.post("/sna/check")
async def sna_check(
    file: UploadFile = File(...),
    kvk: str = Form(""),
    _account: CompanyAccount = Depends(get_company_account),
):
    _, mime, content = await _read_certificate(file, "sna")
    return check_certificate(content, mime, kvk.strip())


@router.post("/registration")
async def registration(
    data: str = Form(...),
    sna: UploadFile | None = File(None),
    iso: UploadFile | None = File(None),
    vca: UploadFile | None = File(None),
    account: CompanyAccount = Depends(get_company_account),
    db: Session = Depends(get_db),
):
    if account.company:
        raise HTTPException(status_code=409, detail="Uw bedrijf is al aangemeld")
    try:
        payload = CompanyRegistration.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
    contractor = payload.company_type == "contractor"
    now = datetime.now(timezone.utc)
    if contractor:
        if not iso or not iso.filename:
            raise HTTPException(status_code=422, detail="Voeg het ISO 9001-certificaat toe")
        if not vca or not vca.filename:
            raise HTTPException(status_code=422, detail="Voeg het VCA-certificaat toe")
        documents = {
            "iso": [await _read_certificate(iso, "iso")],
            "vca": [await _read_certificate(vca, "vca")],
        }
        label, verified, details = "ISO 9001 + VCA", False, {"kind": "contractor"}
    else:
        if not sna or not sna.filename:
            raise HTTPException(status_code=422, detail="Voeg het SNA-certificaat toe")
        certificate = await _read_certificate(sna, "sna")
        details = check_certificate(certificate[2], certificate[1], payload.kvk)
        documents = {"sna": [certificate]}
        label, verified = ("Ja", True) if details["verified"] else ("In controle", False)
    item = Company(
        **payload.model_dump(),
        email=account.email,
        status="pending",
        sna=label,
        sna_verified=verified,
        sna_details=details,
        consent_at=now,
    )
    _save_with_documents(db, item, "company", documents)
    account.company_id = item.id
    db.commit()
    return {"id": item.id, "status": item.status, "email": account.email, "sna_verified": item.sna_verified}


def get_approved_company(account: CompanyAccount = Depends(get_company_account)) -> Company:
    company = account.company
    if not company or company.status != "approved":
        raise HTTPException(status_code=403, detail="Uw bedrijf is nog niet goedgekeurd")
    return company


def _company_docs(db: Session, company_id: int) -> list[dict]:
    rows = (
        db.query(Document)
        .filter(Document.owner_type == "company", Document.owner_id == company_id)
        .order_by(Document.id)
        .all()
    )
    return [
        {
            "id": row.id,
            "kind_label": kind_label("company", row.kind),
            "original_name": row.original_name,
            "url": f"/api/v1/company/documents/{row.id}",
        }
        for row in rows
    ]


def _profile(company: Company, db: Session) -> dict:
    return {
        "company_name": company.company_name,
        "kvk": company.kvk,
        "address": company.address,
        "website": company.website,
        "description": company.description,
        "contact_name": company.contact_name,
        "contact_role": company.contact_role,
        "email": company.email,
        "phone": company.phone,
        "sna_verified": company.sna_verified,
        "documents": _company_docs(db, company.id),
    }


def _selection_profiles(db: Session, request_id: int) -> list[dict]:
    try:
        rows = (
            db.query(Craftsman.id, Craftsman.profession, Craftsman.city)
            .join(RequestSelection, RequestSelection.craftsman_id == Craftsman.id)
            .filter(RequestSelection.request_id == request_id)
            .order_by(Craftsman.id)
            .all()
        )
    except ProgrammingError:
        db.rollback()
        return []
    return [{"id": row.id, "profession": row.profession, "city": row.city or ""} for row in rows]


def _request_out(item: WorkRequest, db: Session) -> dict:
    return {
        "id": item.public_id,
        "worker": item.craftsman_id,
        "project": item.project,
        "job": item.craftsman.profession if item.craftsman else "",
        "date": item.start_date.isoformat() if item.start_date else "",
        "status": REQUEST_LABELS.get(item.status, item.status),
        "site_address": item.site_address,
        "duration": item.duration,
        "schedule": item.schedule,
        "workers_count": item.workers_count,
        "work_description": item.work_description,
        "requirements": item.requirements,
        "last_message": item.messages[-1].body if item.messages else "",
        "manager_messages": sum(1 for msg in item.messages if msg.sender_role == "admin"),
        "messages": [
            {"id": msg.id, "sender_role": msg.sender_role, "body": msg.body, "created_at": msg.created_at.isoformat()}
            for msg in item.messages
        ],
        "selection": _selection_profiles(db, item.id),
    }


def _own_request(db: Session, company: Company, public_id: str) -> WorkRequest:
    item = (
        db.query(WorkRequest)
        .filter(WorkRequest.company_id == company.id, WorkRequest.public_id == public_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Aanvraag niet gevonden")
    return item


@router.get("/profile")
def company_profile(company: Company = Depends(get_approved_company), db: Session = Depends(get_db)):
    return _profile(company, db)


@router.put("/profile")
def update_profile(
    payload: CompanyProfileUpdate,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    for key, value in payload.model_dump().items():
        setattr(company, key, value)
    company.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(company)
    return _profile(company, db)


@router.get("/documents/{document_id}")
def company_document(
    document_id: int,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    row = db.get(Document, document_id)
    if not row or row.owner_type != "company" or row.owner_id != company.id:
        raise HTTPException(status_code=404, detail="Document niet gevonden")
    path = Path(row.stored_path).resolve()
    try:
        path.relative_to(settings.private_uploads_path.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Document niet gevonden")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document niet gevonden")
    return FileResponse(
        path,
        media_type=row.mime_type or None,
        filename=row.original_name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/favorites")
def favorites(company: Company = Depends(get_approved_company), db: Session = Depends(get_db)):
    rows = (
        db.query(CompanyFavorite.craftsman_id)
        .join(Craftsman, Craftsman.id == CompanyFavorite.craftsman_id)
        .filter(CompanyFavorite.company_id == company.id, Craftsman.published.is_(True))
    )
    return {"ids": [row[0] for row in rows]}


@router.post("/favorites/{craftsman_id}")
def toggle_favorite(
    craftsman_id: int,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    craftsman = db.get(Craftsman, craftsman_id)
    if not craftsman or not craftsman.published:
        raise HTTPException(status_code=404, detail="Vakman niet gevonden")
    row = db.query(CompanyFavorite).filter_by(company_id=company.id, craftsman_id=craftsman_id).first()
    if row:
        db.delete(row)
    else:
        db.add(CompanyFavorite(company_id=company.id, craftsman_id=craftsman_id))
    db.commit()
    return favorites(company, db)


@router.get("/picks")
def picks(company: Company = Depends(get_approved_company), db: Session = Depends(get_db)):
    try:
        rows = (
            db.query(CompanyPick.craftsman_id)
            .join(Craftsman, Craftsman.id == CompanyPick.craftsman_id)
            .filter(CompanyPick.company_id == company.id, Craftsman.published.is_(True))
            .order_by(CompanyPick.created_at)
        )
        ids = [row[0] for row in rows]
    except ProgrammingError:
        db.rollback()
        return {"ids": []}
    return {"ids": ids}


@router.post("/picks/{craftsman_id}")
def toggle_pick(
    craftsman_id: int,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    craftsman = db.get(Craftsman, craftsman_id)
    if not craftsman or not craftsman.published:
        raise HTTPException(status_code=404, detail="Vakman niet gevonden")
    row = db.query(CompanyPick).filter_by(company_id=company.id, craftsman_id=craftsman_id).first()
    if row:
        db.delete(row)
    else:
        db.add(CompanyPick(company_id=company.id, craftsman_id=craftsman_id))
    db.commit()
    return picks(company, db)


@router.get("/requests")
def company_requests(company: Company = Depends(get_approved_company), db: Session = Depends(get_db)):
    items = (
        db.query(WorkRequest)
        .filter(WorkRequest.company_id == company.id)
        .order_by(WorkRequest.created_at.desc())
        .all()
    )
    return {"items": [_request_out(item, db) for item in items]}


@router.post("/requests")
def create_company_request(
    payload: CompanyRequestIn,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    if payload.craftsman_id is not None:
        craftsman = db.get(Craftsman, payload.craftsman_id)
        if not craftsman or not craftsman.published:
            raise HTTPException(status_code=404, detail="Vakman niet gevonden")
    now = datetime.now(timezone.utc)
    item = WorkRequest(
        **payload.model_dump(),
        company_id=company.id,
        status="submitted",
        public_id=f"tmp-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.flush()
    item.public_id = f"A-{2000 + item.id}"
    db.commit()
    db.refresh(item)
    return _request_out(item, db)


def _sync_selection(db: Session, item: WorkRequest, company: Company) -> list[Craftsman]:
    picks = (
        db.query(Craftsman)
        .join(CompanyPick, CompanyPick.craftsman_id == Craftsman.id)
        .filter(CompanyPick.company_id == company.id, Craftsman.published.is_(True))
        .order_by(CompanyPick.created_at)
        .all()
    )
    if not picks:
        raise HTTPException(status_code=422, detail="Selecteer eerst een of meer vakmensen.")
    db.query(RequestSelection).filter(RequestSelection.request_id == item.id).delete(synchronize_session=False)
    for craftsman in picks:
        db.add(RequestSelection(request_id=item.id, craftsman_id=craftsman.id))
    return picks


@router.post("/selection/contact")
def contact_about_selection(
    payload: SelectionContactIn,
    background: BackgroundTasks,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    channel = payload.channel if payload.channel in {"chat", "email"} else "chat"
    body = payload.body.strip() or payload.work_description.strip() or (
        "Graag contact per e-mail over deze aanvraag."
        if channel == "email"
        else "Graag deze selectie bespreken in de chat."
    )
    now = datetime.now(timezone.utc)
    item = WorkRequest(
        project=payload.project.strip() or "Selectie",
        site_address=payload.site_address,
        start_date=payload.start_date,
        duration=payload.duration,
        schedule=payload.schedule,
        work_description=payload.work_description,
        requirements=payload.requirements,
        company_id=company.id,
        status="submitted",
        public_id=f"tmp-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.flush()
    item.public_id = f"A-{2000 + item.id}"
    picks = _sync_selection(db, item, company)
    item.workers_count = payload.workers_count or len(picks)
    db.query(CompanyPick).filter(
        CompanyPick.company_id == company.id,
        CompanyPick.craftsman_id.in_([row.id for row in picks]),
    ).delete(synchronize_session=False)
    msg = Message(request_id=item.id, sender_role="company", body=body, created_at=now)
    db.add(msg)
    item.updated_at = now
    db.commit()
    db.refresh(item)
    db.refresh(msg)
    _notify_admin(item, msg)
    emailed = False
    if channel == "email" and settings.smtp_host and settings.smtp_from:
        lines = "\n".join(f"#{row.id} · {row.profession} · {row.city}" for row in picks)
        background.add_task(
            send_mail,
            settings.admin_email,
            f"Selectie van {company.company_name}",
            f"{company.contact_name} <{company.email}>\n{company.company_name}\n\n{body}\n\nGeselecteerde vakmensen:\n{lines}",
        )
        emailed = True
    data = _request_out(item, db)
    data["emailed"] = emailed
    return data


@router.post("/requests/{public_id}/messages")
def company_message(
    public_id: str,
    payload: CompanyMessageIn,
    company: Company = Depends(get_approved_company),
    db: Session = Depends(get_db),
):
    item = _own_request(db, company, public_id)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Schrijf een bericht")
    now = datetime.now(timezone.utc)
    msg = Message(request_id=item.id, sender_role="company", body=body, created_at=now)
    db.add(msg)
    item.updated_at = now
    db.commit()
    db.refresh(item)
    db.refresh(msg)
    _notify_admin(item, msg)
    return _request_out(item, db)


@router.get("/messages/stream")
async def company_message_stream(request: Request, company: Company = Depends(get_approved_company)):
    async def events():
        queue = listen_inbox("company", company.id)
        try:
            yield "retry: 2000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            close_inbox(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _notify_admin(item: WorkRequest, msg: Message) -> None:
    payload = {
        "type": "message",
        "request_id": item.id,
        "message_id": msg.id,
        "sender_role": msg.sender_role,
        "body": msg.body,
        "public_id": item.public_id,
        "project": item.project or "",
        "company_name": item.company.company_name if item.company else "",
        "company_id": item.company_id,
    }
    publish({**payload, "audience": "admin"})
    publish({**payload, "audience": "company"})
