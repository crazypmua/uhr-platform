from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from .config import settings
from .models import Document

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_KIND = 12

DOCUMENT_KINDS = {
    "craftsman": {
        "vca": "Сертифікат VCA",
        "portfolio": "Фото виконаних робіт",
        "tools": "Фото інструментів",
        "vehicle": "Фото робочого автомобіля",
        "certificates": "Інші сертифікати",
        "portrait": "Фото в робочому одязі",
    },
    "company": {
        "company_docs": "Bedrijfsdocumenten",
        "certificates": "Certificaten",
    },
}


async def read_uploads(files: dict[str, list[UploadFile]], owner_type: str) -> dict[str, list[tuple[str, str, bytes]]]:
    """Validates uploads before anything is written to the database."""
    kinds = DOCUMENT_KINDS[owner_type]
    result: dict[str, list[tuple[str, str, bytes]]] = {}
    for kind, items in files.items():
        if kind not in kinds:
            continue
        items = [item for item in items if item.filename]
        if len(items) > MAX_FILES_PER_KIND:
            raise HTTPException(status_code=413, detail=f"Забагато файлів: {kinds[kind]}")
        for item in items:
            if item.content_type not in ALLOWED_MIME:
                raise HTTPException(status_code=415, detail=f"Непідтримуваний формат файлу: {item.filename}")
            content = await item.read(MAX_FILE_BYTES + 1)
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"Файл більший за 10 MB: {item.filename}")
            result.setdefault(kind, []).append((Path(item.filename).name[:255], item.content_type, content))
    return result


def store_documents(db: Session, owner_type: str, owner_id: int, uploads: dict[str, list[tuple[str, str, bytes]]]) -> list[Path]:
    folder = settings.private_uploads_path / owner_type / str(owner_id)
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for kind, items in uploads.items():
        for original_name, mime, content in items:
            path = folder / (uuid4().hex + ALLOWED_MIME[mime])
            path.write_bytes(content)
            written.append(path)
            db.add(Document(
                owner_type=owner_type,
                owner_id=owner_id,
                kind=kind,
                original_name=original_name,
                stored_path=str(path),
                mime_type=mime,
                size_bytes=len(content),
            ))
    return written


def kind_label(owner_type: str, kind: str) -> str:
    return DOCUMENT_KINDS.get(owner_type, {}).get(kind, kind)
