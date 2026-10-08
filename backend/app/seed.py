from sqlalchemy.orm import Session

from .auth import hash_password
from .config import settings
from .models import SiteText, User
from .seed_texts import DEFAULT_TEXTS


def ensure_admin(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if existing:
        return
    db.add(
        User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            name="Менеджер UHR",
        )
    )
    db.commit()


def ensure_texts(db: Session) -> None:
    for site, page, locale, sort_order, key, label, value in DEFAULT_TEXTS:
        found = (
            db.query(SiteText)
            .filter_by(site=site, page=page, key=key, locale=locale)
            .first()
        )
        if found:
            continue
        db.add(
            SiteText(
                site=site,
                page=page,
                key=key,
                locale=locale,
                label=label,
                value=value,
                sort_order=sort_order,
            )
        )
    db.commit()
