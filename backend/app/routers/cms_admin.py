from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import bleach
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..config import settings
from ..db import get_db
from ..models import (
    CmsCatalogCategory,
    CmsMedia,
    CmsMenu,
    CmsMenuVersion,
    CmsPage,
    CmsPageVersion,
    CmsPost,
    CmsPostVersion,
    User,
)
from ..schemas import CmsCategorySave, CmsMenuSave, CmsPageCreate, CmsPageSave, CmsPostSave, dt

router = APIRouter(
    prefix="/admin/cms",
    tags=["cms-admin"],
    dependencies=[Depends(get_current_admin)],
)

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "article", "aside", "blockquote", "br", "button", "div", "figure", "figcaption",
    "footer", "h1", "h2", "h3", "h4", "header", "hr", "img", "main", "nav",
    "p", "section", "small", "span", "strong", "ul", "ol", "li",
}
ALLOWED_ATTRS = {
    "*": ["class", "id", "title", "aria-label", "role"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "button": ["type"],
    "section": ["data-cms-widget", "data-kind", "data-limit"],
    "div": ["data-cms-widget", "data-kind", "data-limit"],
}
ALLOWED_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_UPLOAD = 10 * 1024 * 1024


def clean_html(value: str) -> str:
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols={"http", "https", "mailto", "tel"},
        strip=True,
    )


def clean_css(value: str) -> str:
    lowered = value.lower()
    for forbidden in ("@import", "javascript:", "expression(", "</style"):
        if forbidden in lowered:
            raise HTTPException(status_code=422, detail=f"CSS містить заборонену конструкцію: {forbidden}")
    return value


def page_out(page: CmsPage, db: Session, detail: bool = False) -> dict:
    result = {
        "id": page.id, "site": page.site, "locale": page.locale, "slug": page.slug,
        "title": page.title, "seo_title": page.seo_title,
        "seo_description": page.seo_description,
        "draft_version_id": page.draft_version_id,
        "published_version_id": page.published_version_id,
        "updated_at": dt(page.updated_at),
    }
    if detail:
        draft = db.get(CmsPageVersion, page.draft_version_id) if page.draft_version_id else None
        result["draft"] = version_out(draft) if draft else None
        versions = (
            db.query(CmsPageVersion)
            .filter(CmsPageVersion.page_id == page.id)
            .order_by(CmsPageVersion.version.desc())
            .all()
        )
        result["versions"] = [version_out(item, include_project=False) for item in versions]
    return result


def version_out(item: CmsPageVersion, include_project: bool = True) -> dict:
    data = {
        "id": item.id, "version": item.version, "note": item.note,
        "created_at": dt(item.created_at),
    }
    if include_project:
        data.update({"project_data": item.project_data, "html": item.html, "css": item.css})
    return data


@router.get("/pages")
def pages(site: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CmsPage).order_by(CmsPage.site, CmsPage.slug)
    if site:
        query = query.filter(CmsPage.site == site)
    return [page_out(item, db) for item in query.all()]


@router.post("/pages")
def create_page(payload: CmsPageCreate, db: Session = Depends(get_db)):
    exists = db.query(CmsPage).filter_by(site=payload.site, locale=payload.locale, slug=payload.slug).first()
    if exists:
        raise HTTPException(status_code=409, detail="Сторінка з таким slug вже існує")
    page = CmsPage(**payload.model_dump())
    db.add(page)
    db.commit()
    db.refresh(page)
    return page_out(page, db, detail=True)


@router.get("/pages/{page_id}")
def page_detail(page_id: int, db: Session = Depends(get_db)):
    page = db.get(CmsPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")
    return page_out(page, db, detail=True)


@router.put("/pages/{page_id}/draft")
def save_page(
    page_id: int,
    payload: CmsPageSave,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    page = db.get(CmsPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")
    current = db.get(CmsPageVersion, page.draft_version_id) if page.draft_version_id else None
    if payload.expected_version is not None and (not current or current.version != payload.expected_version):
        raise HTTPException(status_code=409, detail="Сторінку вже змінено в іншій вкладці")
    next_version = (db.query(func.max(CmsPageVersion.version)).filter_by(page_id=page.id).scalar() or 0) + 1
    revision = CmsPageVersion(
        page_id=page.id,
        version=next_version,
        project_data=payload.project_data,
        html=clean_html(payload.html),
        css=clean_css(payload.css),
        note=payload.note,
        created_by=user.id,
    )
    db.add(revision)
    db.flush()
    page.title = payload.title
    page.seo_title = payload.seo_title
    page.seo_description = payload.seo_description
    page.draft_version_id = revision.id
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(page)
    return page_out(page, db, detail=True)


@router.post("/pages/{page_id}/publish")
def publish_page(page_id: int, db: Session = Depends(get_db)):
    page = db.get(CmsPage, page_id)
    if not page or not page.draft_version_id:
        raise HTTPException(status_code=422, detail="Спочатку збережіть чернетку")
    page.published_version_id = page.draft_version_id
    page.updated_at = datetime.now(timezone.utc)
    db.commit()
    return page_out(page, db)


@router.post("/pages/{page_id}/rollback/{version_id}")
def rollback_page(page_id: int, version_id: int, db: Session = Depends(get_db)):
    page = db.get(CmsPage, page_id)
    version = db.get(CmsPageVersion, version_id)
    if not page or not version or version.page_id != page.id:
        raise HTTPException(status_code=404, detail="Версію не знайдено")
    page.draft_version_id = version.id
    db.commit()
    return page_out(page, db, detail=True)


@router.delete("/pages/{page_id}")
def delete_page(page_id: int, db: Session = Depends(get_db)):
    page = db.get(CmsPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")
    db.delete(page)
    db.commit()
    return {"ok": True}


@router.get("/menus/{site}/{area}")
def menu(site: str, area: str, locale: str = "nl", db: Session = Depends(get_db)):
    item = db.query(CmsMenu).filter_by(site=site, locale=locale, area=area).first()
    if not item:
        item = CmsMenu(site=site, locale=locale, area=area, name=area.title())
        db.add(item)
        db.commit()
        db.refresh(item)
    return {"id": item.id, "site": site, "area": area, "version": item.version,
            "draft_items": item.draft_items, "published_items": item.published_items}


@router.put("/menus/{site}/{area}")
def save_menu(site: str, area: str, payload: CmsMenuSave, locale: str = "nl", db: Session = Depends(get_db)):
    item = db.query(CmsMenu).filter_by(site=site, locale=locale, area=area).first()
    if not item:
        item = CmsMenu(site=site, locale=locale, area=area, name=area.title())
        db.add(item)
    item.draft_items = payload.items
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/menus/{site}/{area}/publish")
def publish_menu(
    site: str, area: str, locale: str = "nl",
    user: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    item = db.query(CmsMenu).filter_by(site=site, locale=locale, area=area).first()
    if not item:
        raise HTTPException(status_code=404, detail="Меню не знайдено")
    item.version += 1
    item.published_items = item.draft_items
    db.add(CmsMenuVersion(menu_id=item.id, version=item.version, items=item.draft_items, created_by=user.id))
    db.commit()
    return {"ok": True, "version": item.version}


def post_out(item: CmsPost, full: bool = False) -> dict:
    data = {
        "id": item.id, "site": item.site, "locale": item.locale, "kind": item.kind,
        "slug": item.slug, "title": item.title, "excerpt": item.excerpt,
        "cover_url": item.cover_url, "status": item.status, "version": item.version,
        "published_at": dt(item.published_at), "updated_at": dt(item.updated_at),
    }
    if full:
        data["body"] = item.draft_body
    return data


@router.get("/posts")
def posts(site: str | None = None, kind: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CmsPost).order_by(CmsPost.updated_at.desc())
    if site:
        query = query.filter(CmsPost.site == site)
    if kind:
        query = query.filter(CmsPost.kind == kind)
    return [post_out(item) for item in query.all()]


@router.post("/posts")
def save_post(payload: CmsPostSave, user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(CmsPost).filter_by(
        site=payload.site, locale=payload.locale, kind=payload.kind, slug=payload.slug
    ).first()
    if not item:
        item = CmsPost(site=payload.site, locale=payload.locale, kind=payload.kind,
                       slug=payload.slug, title=payload.title)
        db.add(item)
        db.flush()
    else:
        item.version += 1
    item.title = payload.title
    item.excerpt = payload.excerpt
    item.cover_url = payload.cover_url
    item.draft_body = clean_html(payload.body)
    snapshot = payload.model_dump()
    snapshot["body"] = item.draft_body
    db.add(CmsPostVersion(post_id=item.id, version=item.version, snapshot=snapshot, created_by=user.id))
    db.commit()
    db.refresh(item)
    return post_out(item, full=True)


@router.post("/posts/{post_id}/publish")
def publish_post(post_id: int, db: Session = Depends(get_db)):
    item = db.get(CmsPost, post_id)
    if not item:
        raise HTTPException(status_code=404, detail="Матеріал не знайдено")
    item.published_body = item.draft_body
    item.status = "published"
    item.published_at = datetime.now(timezone.utc)
    db.commit()
    return post_out(item, full=True)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    item = db.get(CmsPost, post_id)
    if not item:
        raise HTTPException(status_code=404, detail="Матеріал не знайдено")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/media")
def media(site: str, db: Session = Depends(get_db)):
    rows = db.query(CmsMedia).filter_by(site=site).order_by(CmsMedia.created_at.desc()).all()
    return [{"id": item.id, "url": item.public_url, "name": item.original_name,
             "mime_type": item.mime_type, "size": item.size_bytes, "alt": item.alt} for item in rows]


@router.post("/media")
async def upload_media(
    site: str = Form(...), alt: str = Form(""), file: UploadFile = File(...),
    user: User = Depends(get_current_admin), db: Session = Depends(get_db),
):
    if site not in {"uhrbv", "ukrwerkspot"} or file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=422, detail="Дозволені JPG, PNG, WebP або GIF")
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Максимальний розмір файлу 10 MB")
    folder = settings.uploads_path / "cms" / site
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + ALLOWED_MIME[file.content_type]
    path = folder / name
    path.write_bytes(content)
    item = CmsMedia(site=site, original_name=Path(file.filename or name).name,
                    stored_path=str(path), public_url=f"/uploads/cms/{site}/{name}",
                    mime_type=file.content_type, size_bytes=len(content), alt=alt, created_by=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "url": item.public_url, "name": item.original_name}


@router.delete("/media/{media_id}")
def delete_media(media_id: int, db: Session = Depends(get_db)):
    item = db.get(CmsMedia, media_id)
    if not item:
        raise HTTPException(status_code=404, detail="Файл не знайдено")
    Path(item.stored_path).unlink(missing_ok=True)
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/categories")
def categories(site: str, db: Session = Depends(get_db)):
    rows = db.query(CmsCatalogCategory).filter_by(site=site).order_by(CmsCatalogCategory.sort_order).all()
    return [{"id": item.id, "site": item.site, "slug": item.slug, "title": item.title,
             "profession": item.profession, "description": item.description,
             "image_url": item.image_url, "sort_order": item.sort_order,
             "is_visible": item.is_visible} for item in rows]


@router.post("/categories")
def save_category(payload: CmsCategorySave, db: Session = Depends(get_db)):
    item = db.query(CmsCatalogCategory).filter_by(site=payload.site, slug=payload.slug).first()
    if not item:
        item = CmsCatalogCategory(site=payload.site, slug=payload.slug, title=payload.title)
        db.add(item)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return {"id": item.id}
