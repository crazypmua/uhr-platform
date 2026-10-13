from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from ..db import get_db
from ..documents import DOCUMENT_KINDS, read_uploads, store_documents
from ..mailer import send_mail
from ..models import Company, Craftsman, Request as WorkRequest, SiteText
from ..notifications import craftsman_received
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


def _validation_detail(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors())


async def _read_application(request: Request, model: type[BaseModel], owner_type: str):
    """Accepts JSON (CMS widget) or multipart with a JSON `data` field plus files."""
    is_multipart = request.headers.get("content-type", "").startswith("multipart/form-data")
    try:
        if is_multipart:
            form = await request.form()
            payload = model.model_validate_json(str(form.get("data") or "{}"))
            files = {
                kind: [value for value in form.getlist(kind) if isinstance(value, UploadFile)]
                for kind in DOCUMENT_KINDS[owner_type]
            }
            uploads = await read_uploads(files, owner_type)
        else:
            payload = model.model_validate(await request.json())
            uploads = {}
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Некоректні дані форми") from exc
    return payload, uploads, is_multipart


def _save_with_documents(db: Session, item, owner_type: str, uploads: dict) -> None:
    db.add(item)
    db.flush()
    written = store_documents(db, owner_type, item.id, uploads)
    try:
        db.commit()
    except Exception:
        db.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    db.refresh(item)


@router.post("/public/applications/craftsmen")
async def create_craftsman(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    payload, uploads, is_multipart = await _read_application(request, CraftsmanApplication, "craftsman")
    if is_multipart and not uploads.get("vca"):
        raise HTTPException(status_code=422, detail="Додайте сертифікат VCA")
    item = Craftsman(**payload.model_dump(), status="pending", consent_at=datetime.now(timezone.utc))
    _save_with_documents(db, item, "craftsman", uploads)
    background.add_task(send_mail, item.email, *craftsman_received(item, uploads))
    return {"id": item.id, "status": item.status}


@router.post("/public/applications/companies")
async def create_company(request: Request, db: Session = Depends(get_db)):
    payload, uploads, is_multipart = await _read_application(request, CompanyApplication, "company")
    if is_multipart and not uploads.get("company_docs"):
        raise HTTPException(status_code=422, detail="Voeg de bedrijfsdocumenten toe")
    item = Company(**payload.model_dump(), status="pending", consent_at=datetime.now(timezone.utc))
    _save_with_documents(db, item, "company", uploads)
    return {"id": item.id, "status": item.status}


@router.post("/public/applications/requests")
def create_request(payload: RequestApplication, db: Session = Depends(get_db)):
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Компанію не знайдено")
    item = WorkRequest(**payload.model_dump(), status="submitted", public_id=f"tmp-{uuid4().hex[:12]}")
    db.add(item)
    db.flush()
    item.public_id = f"A-{2000 + item.id}"
    db.commit()
    db.refresh(item)
    return {"id": item.id, "public_id": item.public_id, "status": item.status}
