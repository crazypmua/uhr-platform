"""Demo data: craftsmen, companies, 50 requests with messages.

Run on the server from the project root:
    .venv/bin/python scripts/seed_demo.py           # add demo data
    .venv/bin/python scripts/seed_demo.py --delete  # remove only demo data

Demo records are recognised by emails like demo.*@example.com.
"""

import argparse
import random
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Company, Craftsman, Document, Message, Request, User  # noqa: E402

DEMO_EMAIL = "demo.%@example.com"
REQUESTS_TOTAL = 50

FIRST_NAMES = ["Олександр", "Андрій", "Сергій", "Дмитро", "Василь", "Іван", "Микола", "Юрій", "Петро", "Богдан",
               "Тарас", "Віктор", "Олег", "Роман", "Максим", "Євген", "Володимир", "Ігор", "Степан", "Артем"]
LAST_NAMES = ["Коваленко", "Шевченко", "Бондаренко", "Ткаченко", "Кравченко", "Олійник", "Мельник", "Поліщук",
              "Савченко", "Лисенко", "Руденко", "Мороз", "Марченко", "Гончар", "Павленко", "Литвин"]
PATRONYMICS = ["Олександрович", "Іванович", "Петрович", "Миколайович", "Васильович", "Сергійович", "Андрійович"]
CITIES = ["Utrecht", "Rotterdam", "Amsterdam", "Eindhoven", "Den Haag", "Gorinchem", "Breda", "Arnhem"]
AVAILABILITY = ["Можу почати зараз", "Можу почати зараз", "Через 2 тижні", "Через місяць"]
WORKS = {
    "Timmerman": "Каркасні роботи, монтаж дахів, підлоги, двері та вікна",
    "Elektricien": "Електропроводка, щитки, освітлення, підключення обладнання",
    "Lasser": "MIG/MAG та TIG зварювання, металоконструкції, огорожі",
    "Schilder": "Фарбування фасадів та інтер’єрів, шпаклювання, підготовка поверхонь",
    "Tegelzetter": "Плитка у ванних та кухнях, великоформатна плитка, гідроізоляція",
    "Loodgieter": "Водопостачання, каналізація, монтаж сантехніки, опалення",
    "Grondwerker": "Земляні роботи, траншеї, укладання бруківки, дренаж",
    "Kabelmonteur": "Прокладання кабелів, з’єднання, підземні мережі",
    "Betonwerker": "Опалубка, армування, заливка бетону, фундаменти",
    "Allround vakman": "Ремонт під ключ: гіпсокартон, плитка, фарбування, дрібна сантехніка",
}
CRAFTSMAN_STATUSES = ["approved"] * 22 + ["pending"] * 5 + ["clarification"] * 2 + ["rejected"] * 1

COMPANIES = [
    ("Bouwbedrijf Parkzicht B.V.", "Gorinchem", "Timmerman"),
    ("Van Dijk Renovatie B.V.", "Utrecht", "Allround vakman"),
    ("De Vries Installatietechniek", "Rotterdam", "Elektricien"),
    ("Bakker Bouw & Onderhoud", "Breda", "Tegelzetter"),
    ("Jansen Infra B.V.", "Arnhem", "Grondwerker"),
    ("Visser Staalbouw", "Eindhoven", "Lasser"),
    ("Mulder Afbouw", "Amsterdam", "Schilder"),
    ("Smit Betonbouw B.V.", "Den Haag", "Betonwerker"),
    ("Meijer Kabel & Netwerk", "Utrecht", "Kabelmonteur"),
    ("Bos Sanitair Service", "Rotterdam", "Loodgieter"),
    ("Hendriks Woningbouw", "Breda", "Timmerman"),
    ("Peters Projectontwikkeling", "Amsterdam", "Allround vakman"),
]
COMPANY_STATUSES = ["approved"] * 9 + ["pending"] * 2 + ["clarification"]
CONTACTS = ["Jan de Boer", "Pieter Bakker", "Sanne Visser", "Mark Jansen", "Lisa de Vries", "Tom Smit",
            "Eva Mulder", "Ruud Peters", "Anouk Bos", "Kees Hendriks", "Femke Meijer", "Bram van Dijk"]
ROLES = ["Projectleider", "Uitvoerder", "Directeur", "Planner", "Werkvoorbereider"]
PROJECTS = ["Renovatie Parkzicht", "Nieuwbouw West", "Kantoor Centrum", "Schoolgebouw De Linde", "Appartementen Havenkwartier",
            "Zorgcentrum Oost", "Bedrijfshal Industrieweg", "Woningen Molenwijk", "Brugherstel N214", "Winkelcentrum Plein"]
STREETS = ["Langendijk", "Stationsweg", "Kerkstraat", "Industrieweg", "Molenweg", "Havenkade", "Schoolstraat"]
DURATIONS = ["2 weken", "1 maand", "6 weken", "3 maanden", "Doorlopend"]
SCHEDULES = ["Ma–vr 07:30–16:00", "Ma–do 07:00–17:00", "Ma–za 07:00–15:30"]
REQUEST_STATUSES = (["submitted"] * 9 + ["in_progress"] * 10 + ["candidate"] * 8 + ["confirmed"] * 10
                    + ["done"] * 9 + ["cancelled"] * 4)
COMPANY_MESSAGES = [
    "Goedemiddag, kunt u bevestigen of de vakman vanaf de startdatum beschikbaar is?",
    "Graag maandag tot vrijdag, van 07:30 tot 16:00.",
    "Is een VCA-certificaat aanwezig? Dat is verplicht op onze bouwplaats.",
    "Kunnen we een kort kennismakingsgesprek plannen?",
    "Bedankt, de planning is akkoord.",
]
ADMIN_MESSAGES = [
    "Welkom! Uw aanvraag is ontvangen. Wij zoeken de best passende vakman.",
    "Wij hebben een kandidaat geselecteerd en stemmen de beschikbaarheid af.",
    "Het VCA-certificaat is gecontroleerd en geldig.",
    "De vakman bevestigt de startdatum. Wij sturen u de details.",
    "Dank u, wij houden u op de hoogte.",
]

PLACEHOLDER_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 120]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\nBT /F1 18 Tf 30 60 Td (Demo document) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
)


def demo_ids(db):
    craftsmen = [row.id for row in db.query(Craftsman.id).filter(Craftsman.email.like(DEMO_EMAIL))]
    companies = [row.id for row in db.query(Company.id).filter(Company.email.like(DEMO_EMAIL))]
    return craftsmen, companies


def add_document(db, owner_type, owner_id, kind, name):
    folder = settings.private_uploads_path / owner_type / str(owner_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"demo-{kind}.pdf"
    path.write_bytes(PLACEHOLDER_PDF)
    db.add(Document(owner_type=owner_type, owner_id=owner_id, kind=kind, original_name=name,
                    stored_path=str(path), mime_type="application/pdf", size_bytes=len(PLACEHOLDER_PDF)))


def delete_demo(db):
    craftsmen, companies = demo_ids(db)
    requests = [row.id for row in db.query(Request.id).filter(
        (Request.company_id.in_(companies)) | (Request.craftsman_id.in_(craftsmen))
    )]
    db.query(Message).filter(Message.request_id.in_(requests)).delete(synchronize_session=False)
    db.query(Request).filter(Request.id.in_(requests)).delete(synchronize_session=False)
    for owner_type, ids in (("craftsman", craftsmen), ("company", companies)):
        db.query(Document).filter(Document.owner_type == owner_type, Document.owner_id.in_(ids)).delete(synchronize_session=False)
        for owner_id in ids:
            shutil.rmtree(settings.private_uploads_path / owner_type / str(owner_id), ignore_errors=True)
    db.query(Craftsman).filter(Craftsman.id.in_(craftsmen)).delete(synchronize_session=False)
    db.query(Company).filter(Company.id.in_(companies)).delete(synchronize_session=False)
    db.commit()
    print(f"Deleted: {len(craftsmen)} craftsmen, {len(companies)} companies, {len(requests)} requests")


def seed(db, rnd):
    now = datetime.now(timezone.utc)
    admin = db.query(User).filter(User.role == "admin").order_by(User.id).first()

    craftsmen = []
    for index, status in enumerate(CRAFTSMAN_STATUSES):
        profession = list(WORKS)[index % len(WORKS)]
        created = now - timedelta(days=rnd.randint(5, 75), hours=rnd.randint(0, 23))
        with_company = index % 4 == 1
        item = Craftsman(
            status=status,
            published=status == "approved",
            name=f"{rnd.choice(LAST_NAMES)} {rnd.choice(FIRST_NAMES)} {rnd.choice(PATRONYMICS)}",
            phone=f"+31 6 {rnd.randint(10000000, 99999999)}",
            email=f"demo.craftsman{index + 1}@example.com",
            language="Українська",
            company_name=f"{rnd.choice(LAST_NAMES)} Bouw ZZP" if with_company else "",
            kvk=str(rnd.randint(10000000, 99999999)) if with_company or rnd.random() < 0.5 else "",
            profession=profession,
            works=WORKS[profession],
            experience_ua=f"{rnd.randint(3, 18)} років",
            experience_nl=f"{rnd.randint(0, 6)} років",
            experience_years=rnd.randint(4, 20),
            hourly_rate=rnd.randint(32, 48),
            city=rnd.choice(CITIES),
            radius_km=rnd.choice([30, 50, 60, 80, 100]),
            availability=rnd.choice(AVAILABILITY),
            nationwide=rnd.random() < 0.4,
            description=f"{profession}: {WORKS[profession].lower()}. Акуратна робота, дотримання термінів і правил безпеки.",
            admin_comment="Додайте чіткіше фото сертифіката VCA." if status == "clarification" else "",
            consent_at=created,
            created_at=created,
            updated_at=created,
        )
        db.add(item)
        db.flush()
        add_document(db, "craftsman", item.id, "vca", "VCA-certificaat.pdf")
        craftsmen.append(item)

    companies = []
    for index, ((name, city, profession), status) in enumerate(zip(COMPANIES, COMPANY_STATUSES)):
        created = now - timedelta(days=rnd.randint(20, 90))
        item = Company(
            status=status,
            company_name=name,
            kvk=str(rnd.randint(10000000, 99999999)),
            btw=f"NL{rnd.randint(100000000, 999999999)}B01",
            address=f"{rnd.choice(STREETS)} {rnd.randint(1, 120)}, {city}",
            website=f"https://{name.split()[0].lower()}-{index + 1}.example.com",
            description=f"Bouwbedrijf uit {city}, actief in renovatie en nieuwbouw.",
            contact_name=CONTACTS[index],
            contact_role=rnd.choice(ROLES),
            email=f"demo.company{index + 1}@example.com",
            phone=f"+31 {rnd.randint(10, 79)} {rnd.randint(1000000, 9999999)}",
            region=city,
            desired_profession=profession,
            expected_count=rnd.randint(1, 8),
            sna=rnd.choice(["Ja", "Nee", "In aanvraag"]),
            consent_at=created,
            created_at=created,
            updated_at=created,
        )
        db.add(item)
        db.flush()
        add_document(db, "company", item.id, "company_docs", "KVK-uittreksel.pdf")
        companies.append(item)

    approved_companies = [item for item in companies if item.status == "approved"]
    published = [item for item in craftsmen if item.published]
    statuses = REQUEST_STATUSES[:REQUESTS_TOTAL]
    rnd.shuffle(statuses)
    for status in statuses:
        company = rnd.choice(approved_companies)
        matching = [item for item in published if item.profession == company.desired_profession] or published
        craftsman = None if status == "submitted" else rnd.choice(matching)
        created = now - timedelta(days=rnd.randint(1, 60), hours=rnd.randint(0, 23))
        start = (created + timedelta(days=rnd.randint(7, 30))).date()
        item = Request(
            public_id=f"tmp-{rnd.getrandbits(48):012x}",
            company_id=company.id,
            craftsman_id=craftsman.id if craftsman else None,
            project=rnd.choice(PROJECTS),
            site_address=f"{rnd.choice(STREETS)} {rnd.randint(1, 200)}, {company.region}",
            start_date=start if status != "done" else min(start, date.today() - timedelta(days=3)),
            duration=rnd.choice(DURATIONS),
            schedule=rnd.choice(SCHEDULES),
            workers_count=rnd.randint(1, 4),
            work_description=f"Werkzaamheden: {WORKS[(craftsman or rnd.choice(published)).profession].lower()}.",
            requirements="VCA verplicht, eigen gereedschap." if rnd.random() < 0.6 else "",
            status=status,
            admin_comment="Opdrachtgever heeft het project uitgesteld." if status == "cancelled" else "",
            created_at=created,
            updated_at=created,
        )
        db.add(item)
        db.flush()
        item.public_id = f"A-{2000 + item.id}"
        moment = created
        for turn in range(rnd.randint(1, 5)):
            moment += timedelta(hours=rnd.randint(1, 30))
            from_company = turn % 2 == 0
            db.add(Message(
                request_id=item.id,
                sender_role="company" if from_company else "admin",
                sender_id=None if from_company else (admin.id if admin else None),
                body=(COMPANY_MESSAGES if from_company else ADMIN_MESSAGES)[turn % 5],
                created_at=moment,
            ))
        item.updated_at = moment
    db.commit()
    print(f"Added: {len(craftsmen)} craftsmen ({len(published)} published), {len(companies)} companies, "
          f"{len(statuses)} requests")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="remove demo data only")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.delete:
            delete_demo(db)
            return
        if any(demo_ids(db)):
            print("Demo data already exists. Run with --delete first to recreate it.")
            return
        seed(db, random.Random(2026))
    finally:
        db.close()


if __name__ == "__main__":
    main()
