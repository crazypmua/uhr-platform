from .config import settings
from .documents import kind_label
from .models import Company, Craftsman

CRAFTSMAN_FIELDS = [
    ("name", "ПІБ"),
    ("phone", "Телефон"),
    ("email", "Email"),
    ("profession", "Вид діяльності"),
    ("works", "Перелік робіт"),
    ("experience_ua", "Досвід роботи в Україні"),
    ("experience_nl", "Досвід роботи в Нідерландах"),
    ("company_name", "Компанія"),
    ("kvk", "KVK"),
    ("btw", "BTW"),
    ("address", "Адреса"),
    ("city", "Місто"),
    ("radius_km", "Радіус роботи, км"),
    ("hourly_rate", "Ставка €/год"),
    ("availability", "Доступність"),
    ("extra_work", "Додаткові види робіт"),
    ("description", "Опис досвіду"),
    ("website", "Сайт"),
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("tiktok", "TikTok"),
    ("portfolio_url", "Портфоліо"),
]


def craftsman_received(item: Craftsman, uploads: dict[str, list]) -> tuple[str, str]:
    lines = [
        f"{label}: {value}"
        for key, label in CRAFTSMAN_FIELDS
        if (value := getattr(item, key)) not in (None, "")
    ]
    if item.nationwide:
        lines.append("Можу працювати по всій території Нідерландів: так")
    files = [f"{kind_label('craftsman', kind)}: {len(items)}" for kind, items in uploads.items()]
    body = (
        f"Вітаємо, {item.name}!\n\n"
        f"Ми отримали вашу анкету на Ukrwerkspot (№ {item.id}). "
        "Менеджер перевірить її протягом 2–3 робочих днів і повідомить вас про результат.\n\n"
        "Ваші дані:\n" + "\n".join(lines)
    )
    if files:
        body += "\n\nЗавантажені файли:\n" + "\n".join(files)
    body += "\n\nЯкщо ви помітили помилку, дайте відповідь на цей лист.\n\nКоманда Ukrwerkspot"
    return "Ukrwerkspot: ми отримали вашу анкету", body


def craftsman_approved(item: Craftsman) -> tuple[str, str]:
    link = settings.craftsman_approved_url or settings.ukrwerkspot_url
    body = (
        f"Вітаємо, {item.name}!\n\n"
        f"Вашу анкету на Ukrwerkspot (№ {item.id}) схвалено. "
        "Ваш професійний профіль опубліковано для перевірених компаній — без імені та контактів.\n\n"
        f"Детальніше за посиланням:\n{link}\n\n"
        "Команда Ukrwerkspot"
    )
    return "Ukrwerkspot: вашу анкету схвалено", body


def company_approved(item: Company) -> tuple[str, str]:
    body = (
        f"Beste {item.contact_name or item.company_name},\n\n"
        f"De registratie van {item.company_name} bij UHR is goedgekeurd. "
        "U kunt nu inloggen en gecontroleerde vakmensen bekijken en aanvragen.\n\n"
        f"Inloggen:\n{settings.uhrbv_url.rstrip('/')}/#login\n\n"
        "Met vriendelijke groet,\nUHR"
    )
    return "UHR: uw registratie is goedgekeurd", body


def company_password_reset(link: str) -> tuple[str, str]:
    body = (
        "U heeft een nieuw wachtwoord aangevraagd voor uw UHR-account.\n\n"
        "Kies een nieuw wachtwoord via deze link. De link is 1 uur geldig:\n"
        f"{link}\n\n"
        "Heeft u dit niet aangevraagd? Dan kunt u deze e-mail negeren.\n\n"
        "Met vriendelijke groet,\nUHR"
    )
    return "UHR: wachtwoord herstellen", body
