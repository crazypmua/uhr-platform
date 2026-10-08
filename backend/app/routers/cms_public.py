from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import has_admin_session, has_preview_access
from ..db import get_db
from ..models import (
    CmsCatalogCategory,
    CmsMenu,
    CmsPage,
    CmsPageVersion,
    CmsPost,
    Craftsman,
)
from ..schemas import dt

router = APIRouter(prefix="/public/cms", tags=["cms-public"])


def can_preview(request: Request, site: str) -> bool:
    return has_preview_access(request, site) or (site == "uhrbv" and has_admin_session(request))


@router.get("/pages/{site}/{slug:path}")
def page(site: str, slug: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CmsPage).filter_by(site=site, slug=slug or "home")
    if locale:
        query = query.filter(CmsPage.locale == locale)
    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")
    version_id = item.draft_version_id if can_preview(request, site) else item.published_version_id
    version = db.get(CmsPageVersion, version_id) if version_id else None
    if not version:
        raise HTTPException(status_code=404, detail="Сторінку ще не опубліковано")
    return {
        "id": item.id,
        "site": item.site,
        "slug": item.slug,
        "locale": item.locale,
        "title": item.title,
        "seo_title": item.seo_title,
        "seo_description": item.seo_description,
        "version": version.version,
        "html": version.html,
        "css": version.css,
        "project_data": version.project_data if can_preview(request, site) else None,
    }


@router.get("/menus/{site}/{area}")
def menu(site: str, area: str, request: Request, locale: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CmsMenu).filter_by(site=site, area=area)
    if locale:
        query = query.filter(CmsMenu.locale == locale)
    item = query.first()
    if not item:
        return {"items": []}
    return {"items": item.draft_items if can_preview(request, site) else item.published_items}


@router.get("/posts/{site}")
def posts(site: str, kind: str = "blog", limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(CmsPost)
        .filter_by(site=site, kind=kind, status="published")
        .order_by(CmsPost.published_at.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return [{
        "id": item.id, "slug": item.slug, "title": item.title, "excerpt": item.excerpt,
        "cover_url": item.cover_url, "body": item.published_body,
        "published_at": dt(item.published_at),
    } for item in rows]


@router.get("/posts/{site}/{kind}/{slug}")
def post(site: str, kind: str, slug: str, db: Session = Depends(get_db)):
    item = db.query(CmsPost).filter_by(site=site, kind=kind, slug=slug, status="published").first()
    if not item:
        raise HTTPException(status_code=404, detail="Матеріал не знайдено")
    return {"slug": item.slug, "title": item.title, "excerpt": item.excerpt,
            "cover_url": item.cover_url, "body": item.published_body,
            "published_at": dt(item.published_at)}


@router.get("/catalog/{site}")
def catalog(site: str, db: Session = Depends(get_db)):
    categories = (
        db.query(CmsCatalogCategory)
        .filter_by(site=site, is_visible=True)
        .order_by(CmsCatalogCategory.sort_order)
        .all()
    )
    workers = db.query(Craftsman).filter(Craftsman.published.is_(True)).order_by(Craftsman.id.desc()).all()
    return {
        "categories": [{
            "slug": item.slug, "title": item.title, "profession": item.profession,
            "description": item.description, "image_url": item.image_url,
        } for item in categories],
        "workers": [{
            "id": item.id,
            "profession": item.profession,
            "experience_years": item.experience_years,
            "hourly_rate": float(item.hourly_rate) if item.hourly_rate is not None else None,
            "city": item.city,
            "radius_km": item.radius_km,
            "availability": item.availability,
            "nationwide": item.nationwide,
            "description": item.description,
            "portfolio_url": item.portfolio_url,
        } for item in workers],
    }
