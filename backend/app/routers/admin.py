from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import create_preview_token, get_current_admin
from ..config import settings
from ..db import get_db
from ..models import Company, Craftsman, Document, Message, Request, SiteText, User
from ..schemas import MessageIn, RequestStatusUpdate, SiteSettingsUpdate, StatusUpdate, TextsPut, d, dt
from ..seed_texts import PAGES, SITES

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

CRAFTSMAN_STATUSES = {
    "pending": "На перевірці",
    "clarification": "Уточнення",
    "approved": "Схвалено",
    "rejected": "Відхилено",
}
REQUEST_STATUSES = {
    "draft": "Concept",
    "submitted": "Ingediend",
    "in_progress": "In behandeling",
    "candidate": "Kandidaat geselecteerd",
    "confirmed": "Bevestigd",
    "done": "Afgerond",
    "cancelled": "Geannuleerd",
}
SITE_LABELS = {
    "ukrwerkspot": "Ukrwerkspot",
    "uhrbv": "UHR",
}


def _docs(db: Session, owner_type: str, owner_id: int) -> list[dict]:
    rows = (
        db.query(Document)
        .filter(Document.owner_type == owner_type, Document.owner_id == owner_id)
        .order_by(Document.id)
        .all()
    )
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "original_name": row.original_name,
            "created_at": dt(row.created_at),
        }
        for row in rows
    ]


def _craftsman_out(item: Craftsman, db: Session, full: bool = False) -> dict:
    data = {
        "id": item.id,
        "status": item.status,
        "status_label": CRAFTSMAN_STATUSES.get(item.status, item.status),
        "published": item.published,
        "name": item.name,
        "profession": item.profession,
        "city": item.city,
        "email": item.email,
        "phone": item.phone,
        "created_at": dt(item.created_at),
        "source": "Ukrwerkspot",
    }
    if not full:
        return data
    data.update(
        {
            "language": item.language,
            "company_name": item.company_name,
            "kvk": item.kvk,
            "btw": item.btw,
            "address": item.address,
            "website": item.website,
            "instagram": item.instagram,
            "facebook": item.facebook,
            "tiktok": item.tiktok,
            "extra_work": item.extra_work,
            "experience_years": item.experience_years,
            "hourly_rate": float(item.hourly_rate) if item.hourly_rate is not None else None,
            "radius_km": item.radius_km,
            "availability": item.availability,
            "nationwide": item.nationwide,
            "description": item.description,
            "portfolio_url": item.portfolio_url,
            "admin_comment": item.admin_comment,
            "consent_at": dt(item.consent_at),
            "updated_at": dt(item.updated_at),
            "documents": _docs(db, "craftsman", item.id),
        }
    )
    return data


def _company_out(item: Company, db: Session, full: bool = False) -> dict:
    data = {
        "id": item.id,
        "status": item.status,
        "status_label": CRAFTSMAN_STATUSES.get(item.status, item.status),
        "company_name": item.company_name,
        "contact_name": item.contact_name,
        "email": item.email,
        "phone": item.phone,
        "created_at": dt(item.created_at),
        "source": "UHR",
    }
    if not full:
        return data
    data.update(
        {
            "kvk": item.kvk,
            "btw": item.btw,
            "address": item.address,
            "website": item.website,
            "description": item.description,
            "contact_role": item.contact_role,
            "region": item.region,
            "desired_profession": item.desired_profession,
            "expected_count": item.expected_count,
            "sna": item.sna,
            "admin_comment": item.admin_comment,
            "consent_at": dt(item.consent_at),
            "updated_at": dt(item.updated_at),
            "documents": _docs(db, "company", item.id),
        }
    )
    return data


def _apply_status(item: Craftsman | Company, payload: StatusUpdate) -> None:
    item.status = payload.status
    item.admin_comment = payload.comment
    item.updated_at = datetime.now(timezone.utc)
    if isinstance(item, Craftsman):
        item.published = payload.status == "approved"


def _site_setting(db: Session, site: str) -> SiteText:
    if site not in SITE_LABELS:
        raise HTTPException(status_code=404, detail="Сайт не знайдено")
    row = (
        db.query(SiteText)
        .filter_by(site=site, page="settings", key="is_open", locale="system")
        .first()
    )
    if not row:
        row = SiteText(
            site=site,
            page="settings",
            key="is_open",
            locale="system",
            label="Сайт відкритий",
            value="false",
        )
        db.add(row)
        db.flush()
    return row


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    new_masters = db.query(func.count(Craftsman.id)).filter(Craftsman.status == "pending").scalar()
    companies_review = db.query(func.count(Company.id)).filter(Company.status == "pending").scalar()
    active_requests = (
        db.query(func.count(Request.id))
        .filter(Request.status.notin_(["done", "cancelled"]))
        .scalar()
    )
    published = db.query(func.count(Craftsman.id)).filter(Craftsman.published.is_(True)).scalar()
    return {
        "new_masters": new_masters or 0,
        "companies_review": companies_review or 0,
        "active_requests": active_requests or 0,
        "published_profiles": published or 0,
    }


@router.get("/sites")
def sites(db: Session = Depends(get_db)):
    result = []
    for site, label in SITE_LABELS.items():
        row = _site_setting(db, site)
        result.append(
            {
                "site": site,
                "label": label,
                "url": settings.site_url(site),
                "is_open": row.value.lower() == "true",
            }
        )
    db.commit()
    return result


@router.put("/sites/{site}")
def update_site(site: str, payload: SiteSettingsUpdate, db: Session = Depends(get_db)):
    row = _site_setting(db, site)
    row.value = "true" if payload.is_open else "false"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"site": site, "is_open": payload.is_open}


@router.get("/sites/{site}/preview-link")
def preview_link(site: str, user: User = Depends(get_current_admin)):
    if site not in SITE_LABELS:
        raise HTTPException(status_code=404, detail="Сайт не знайдено")
    token = create_preview_token(site, user)
    return {
        "url": f"{settings.site_url(site)}/api/v1/auth/preview?token={token}",
        "expires_in_seconds": 300,
    }


@router.get("/craftsmen")
def craftsmen(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Craftsman).order_by(Craftsman.created_at.desc())
    if status:
        query = query.filter(Craftsman.status == status)
    return [_craftsman_out(item, db) for item in query.all()]


@router.get("/craftsmen/{item_id}")
def craftsman_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Craftsman, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Анкету не знайдено")
    return _craftsman_out(item, db, full=True)


@router.post("/craftsmen/{item_id}/status")
def craftsman_status(item_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    item = db.get(Craftsman, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Анкету не знайдено")
    _apply_status(item, payload)
    db.commit()
    db.refresh(item)
    return _craftsman_out(item, db, full=True)


@router.get("/companies")
def companies(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Company).order_by(Company.created_at.desc())
    if status:
        query = query.filter(Company.status == status)
    return [_company_out(item, db) for item in query.all()]


@router.get("/companies/{item_id}")
def company_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Company, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Компанію не знайдено")
    return _company_out(item, db, full=True)


@router.post("/companies/{item_id}/status")
def company_status(item_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    item = db.get(Company, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Компанію не знайдено")
    _apply_status(item, payload)
    db.commit()
    db.refresh(item)
    return _company_out(item, db, full=True)


@router.get("/requests")
def requests(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Request).order_by(Request.created_at.desc())
    if status:
        query = query.filter(Request.status == status)
    return [
        {
            "id": item.id,
            "public_id": item.public_id,
            "project": item.project,
            "status": item.status,
            "status_label": REQUEST_STATUSES.get(item.status, item.status),
            "start_date": d(item.start_date),
            "company_name": item.company.company_name if item.company else "",
            "profession": item.craftsman.profession if item.craftsman else "",
            "created_at": dt(item.created_at),
        }
        for item in query.all()
    ]


@router.get("/requests/{item_id}")
def request_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Request, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    return {
        "id": item.id,
        "public_id": item.public_id,
        "project": item.project,
        "site_address": item.site_address,
        "start_date": d(item.start_date),
        "duration": item.duration,
        "schedule": item.schedule,
        "workers_count": item.workers_count,
        "work_description": item.work_description,
        "requirements": item.requirements,
        "status": item.status,
        "status_label": REQUEST_STATUSES.get(item.status, item.status),
        "admin_comment": item.admin_comment,
        "company": _company_out(item.company, db) if item.company else None,
        "craftsman": _craftsman_out(item.craftsman, db) if item.craftsman else None,
        "messages": [
            {
                "id": msg.id,
                "sender_role": msg.sender_role,
                "body": msg.body,
                "created_at": dt(msg.created_at),
            }
            for msg in item.messages
        ],
    }


@router.post("/requests/{item_id}/status")
def request_status(item_id: int, payload: RequestStatusUpdate, db: Session = Depends(get_db)):
    item = db.get(Request, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    item.status = payload.status
    item.admin_comment = payload.comment
    if payload.craftsman_id is not None:
        item.craftsman_id = payload.craftsman_id
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": item.status}


@router.get("/messages")
def messages(request_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Request).order_by(Request.updated_at.desc())
    threads = []
    for item in query.all():
        last = item.messages[-1] if item.messages else None
        threads.append(
            {
                "id": item.id,
                "public_id": item.public_id,
                "project": item.project,
                "company_name": item.company.company_name if item.company else "",
                "last_message": last.body if last else "",
                "updated_at": dt(last.created_at if last else item.created_at),
            }
        )
    current = None
    if request_id:
        item = db.get(Request, request_id)
        if item:
            current = {
                "id": item.id,
                "public_id": item.public_id,
                "project": item.project,
                "messages": [
                    {
                        "id": msg.id,
                        "sender_role": msg.sender_role,
                        "body": msg.body,
                        "created_at": dt(msg.created_at),
                    }
                    for msg in item.messages
                ],
            }
    return {"threads": threads, "current": current}


@router.post("/messages")
def send_message(payload: MessageIn, user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.get(Request, payload.request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Заявку не знайдено")
    msg = Message(request_id=item.id, sender_role="admin", sender_id=user.id, body=payload.body.strip())
    db.add(msg)
    db.commit()
    return {"ok": True, "id": msg.id}


@router.get("/texts/meta")
def texts_meta():
    return {
        "sites": [{"id": key, "label": label} for key, label in SITES],
        "pages": {
            site: [{"id": key, "label": label} for key, label in pages]
            for site, pages in PAGES.items()
        },
    }


@router.get("/texts")
def texts(site: str, page: str, locale: str | None = None, db: Session = Depends(get_db)):
    query = db.query(SiteText).filter(SiteText.site == site, SiteText.page == page)
    if locale:
        query = query.filter(SiteText.locale == locale)
    rows = query.order_by(SiteText.sort_order, SiteText.id).all()
    return [
        {
            "id": row.id,
            "site": row.site,
            "page": row.page,
            "key": row.key,
            "locale": row.locale,
            "label": row.label,
            "value": row.value,
            "updated_at": dt(row.updated_at),
        }
        for row in rows
    ]


@router.put("/texts")
def save_texts(payload: TextsPut, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    for item in payload.items:
        row = db.get(SiteText, item.id)
        if not row:
            continue
        row.value = item.value
        row.updated_at = now
    db.commit()
    return {"ok": True, "saved": len(payload.items)}
