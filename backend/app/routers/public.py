from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company, Craftsman, Request, SiteText
from ..schemas import CompanyApplication, CraftsmanApplication, RequestApplication

router = APIRouter(tags=["public"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/public/texts")
def public_texts(site: str, page: str, locale: str | None = None, db: Session = Depends(get_db)):
    query = db.query(SiteText).filter(SiteText.site == site, SiteText.page == page)
    if locale:
        query = query.filter(SiteText.locale == locale)
    rows = query.order_by(SiteText.sort_order, SiteText.id).all()
    return {row.key: row.value for row in rows}


@router.post("/public/applications/craftsmen")
def create_craftsman(payload: CraftsmanApplication, db: Session = Depends(get_db)):
    item = Craftsman(
        **payload.model_dump(),
        status="pending",
        consent_at=datetime.now(timezone.utc),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": item.status}


@router.post("/public/applications/companies")
def create_company(payload: CompanyApplication, db: Session = Depends(get_db)):
    item = Company(
        **payload.model_dump(),
        status="pending",
        consent_at=datetime.now(timezone.utc),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": item.status}


@router.post("/public/applications/requests")
def create_request(payload: RequestApplication, db: Session = Depends(get_db)):
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компанію не знайдено")
    item = Request(**payload.model_dump(), status="submitted", public_id=f"tmp-{uuid4().hex[:12]}")
    db.add(item)
    db.flush()
    item.public_id = f"A-{2000 + item.id}"
    db.commit()
    db.refresh(item)
    return {"id": item.id, "public_id": item.public_id, "status": item.status}
