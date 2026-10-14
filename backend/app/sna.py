"""SNA certificate: reads the PDF text and looks the KvK number up in the public SNA register."""
import html
import io
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from pypdf import PdfReader

log = logging.getLogger(__name__)

REGISTER_URL = "https://www.normeringarbeid.nl/snakeurmerk/gecertificeerde-ondernemingen"
KVK_RE = re.compile(r"(?:KvK|Kamer van Koophandel)[^\d\n]{0,20}(\d{8})", re.I)
DATE_RE = re.compile(r"(?:Datum|Date)\s*:?\s*(\d{1,2}-\d{1,2}-\d{4})", re.I)
HOLDER_RE = re.compile(r"(?:vastgesteld dat|established that)\s*\n\s*(.+?)\s*\n\s*(.+?)\s*\n", re.I)
COLUMN_RE = re.compile(r'<div class="col[^"]*">(.*?)</div>', re.S)


def _clean(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", ", ", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", text)).strip(" ,")


def read_certificate(content: bytes, mime: str) -> dict:
    """Scans and photos have no text layer; then the company enters the KvK number itself."""
    if mime != "application/pdf":
        return {}
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages[:3])
    except Exception as exc:
        log.warning("Cannot read SNA certificate: %s", exc)
        return {}
    data = {"is_sna": "normering arbeid" in text.lower()}
    if match := KVK_RE.search(text):
        data["kvk"] = match.group(1)
    if match := DATE_RE.search(text):
        data["date"] = match.group(1)
    if match := HOLDER_RE.search(text):
        data["company_name"], data["city"] = match.group(1), match.group(2)
    return data


def lookup_register(kvk: str) -> dict | None:
    """None means the register could not be reached, not that the company is missing."""
    url = REGISTER_URL + "?" + urllib.parse.urlencode({"filters[kvk]": kvk})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "UHR/1.0"}), timeout=10) as response:
            page = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        log.warning("SNA register unavailable: %s", exc)
        return None
    for chunk in page.split('class="result-row"')[1:]:
        columns = [_clean(value) for value in COLUMN_RE.findall(chunk)]
        if len(columns) < 4 or kvk not in columns[2]:
            continue
        return {
            "found": True,
            "company_name": columns[0],
            "address": columns[1],
            "activities": [item.strip() for item in columns[3].split("•") if item.strip()],
        }
    return {"found": False}


def check_certificate(content: bytes, mime: str, kvk: str = "") -> dict:
    extracted = read_certificate(content, mime)
    kvk = kvk or extracted.get("kvk", "")
    register = lookup_register(kvk) if re.fullmatch(r"\d{8}", kvk) else None
    kvk_matches = not extracted.get("kvk") or extracted["kvk"] == kvk
    # Verified only when the uploaded certificate itself carries the KvK number found in the register
    return {
        "extracted": extracted,
        "kvk": kvk,
        "kvk_matches": kvk_matches,
        "register": register,
        "verified": bool(register and register.get("found") and extracted.get("kvk") == kvk),
        "register_url": REGISTER_URL + "?" + urllib.parse.urlencode({"filters[kvk]": kvk}) if kvk else REGISTER_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
