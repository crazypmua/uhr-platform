from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import has_admin_session, has_preview_access
from .config import ROOT, settings
from .db import SessionLocal
from .models import SiteText
from .routers import admin, auth, public
from .seed import ensure_admin, ensure_texts


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        ensure_admin(db)
        ensure_texts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="UHR", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

admin_dir = ROOT / "frontend" / "admin"
ukr_dir = ROOT / "frontend" / "ukrwerkspot"
uhr_dir = ROOT / "frontend" / "uhrbv"
uploads = settings.uploads_path

if uploads.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads)), name="uploads")
if admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(admin_dir), html=True), name="admin")


def _site_from_request(request: Request) -> tuple[str, Path]:
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if "ukrwerkspot" in host:
        return "ukrwerkspot", ukr_dir
    return "uhrbv", uhr_dir


def _site_is_open(site: str) -> bool:
    db = SessionLocal()
    try:
        row = (
            db.query(SiteText)
            .filter_by(site=site, page="settings", key="is_open", locale="system")
            .first()
        )
        return bool(row and row.value.lower() == "true")
    finally:
        db.close()


def _safe_file(base: Path, path: str) -> Path | None:
    base = base.resolve()
    candidate = (base / path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


@app.get("/{path:path}", include_in_schema=False)
def site_frontend(path: str, request: Request):
    site, site_dir = _site_from_request(request)
    can_preview = has_preview_access(request, site)
    if site == "uhrbv":
        can_preview = can_preview or has_admin_session(request)
    frontend_dir = site_dir / "preview" if _site_is_open(site) or can_preview else site_dir
    requested = _safe_file(frontend_dir, path) if path else None
    response_file = requested or frontend_dir / "index.html"
    headers = None
    if response_file.name == "index.html":
        headers = {"Cache-Control": "no-store, max-age=0"}
    return FileResponse(response_file, headers=headers)
