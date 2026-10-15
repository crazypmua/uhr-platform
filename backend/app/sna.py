"""SNA certificate: reads a PDF or a photo and looks the KvK number up in the public SNA register."""
import html
import io
import logging
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from pypdf import PdfReader

log = logging.getLogger(__name__)

REGISTER_URL = "https://www.normeringarbeid.nl/snakeurmerk/gecertificeerde-ondernemingen"
KVK_RE = re.compile(r"(?:KvK|Kamer van Koophandel)[^\d]{0,30}(\d{8})", re.I)
DATE_RE = re.compile(r"(?:Datum|Date)\s*:?\s*(\d{1,2}-\d{1,2}-\d{4})", re.I)
HOLDER_RE = re.compile(r"(?:vastgesteld dat|established that)\s*\n\s*(.+?)\s*\n\s*(.+?)\s*\n", re.I)
COLUMN_RE = re.compile(r'<div class="col[^"]*">(.*?)</div>', re.S)
_ocr_engine = None
_ocr_lock = threading.Lock()


def _clean(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", ", ", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", text)).strip(" ,")


def _engine():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _ocr_text(result) -> str:
    if result is None:
        return ""
    lines = getattr(result, "txts", None)
    if lines:
        return "\n".join(lines)
    rows = result[0] if isinstance(result, tuple) else result
    if isinstance(rows, list):
        return "\n".join(row[1] for row in rows if isinstance(row, (list, tuple)) and len(row) > 1)
    return ""


def _ocr_image(image) -> str:
    from PIL import Image
    image = image.convert("RGB")
    longest = max(image.size)
    if longest < 1800:
        scale = 1800 / longest
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    import numpy as np
    with _ocr_lock:
        result = _engine()(np.array(image))
    return _ocr_text(result)


def _ocr_bytes(content: bytes) -> str:
    from PIL import Image
    return _ocr_image(Image.open(io.BytesIO(content)))


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages[:3])


def _ocr_pdf(content: bytes) -> str:
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(content)
    parts = []
    try:
        for index in range(min(2, len(document))):
            page = document[index]
            bitmap = page.render(scale=2)
            try:
                parts.append(_ocr_image(bitmap.to_pil()))
            finally:
                bitmap.close()
    finally:
        document.close()
    return "\n".join(part for part in parts if part)


def _looks_like_date(value: str) -> bool:
    day, month, year = int(value[:2]), int(value[2:4]), int(value[4:])
    if 1 <= day <= 31 and 1 <= month <= 12 and 1990 <= year <= 2100:
        return True
    year, month, day = int(value[:4]), int(value[4:6]), int(value[6:])
    return 1990 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31


def _kvk_from_text(text: str) -> str:
    text = re.sub(r"(?<=\d)[ \t]+(?=\d)", "", text)
    if match := KVK_RE.search(text):
        return match.group(1)
    numbers = [item for item in re.findall(r"(?<!\d)(\d{8})(?!\d)", text) if not _looks_like_date(item)]
    unique = list(dict.fromkeys(numbers))
    mentioned = re.search(r"normering|verklaring|certificaat|inschrijving", text, re.I)
    if len(unique) == 1 and (mentioned or "kvk" in text.lower()):
        return unique[0]
    return ""


def _parse(text: str) -> dict:
    if not text.strip():
        return {}
    data = {"is_sna": "normering arbeid" in text.lower() or "verklaring van registratie" in text.lower()}
    if kvk := _kvk_from_text(text):
        data["kvk"] = kvk
    if match := DATE_RE.search(text):
        data["date"] = match.group(1)
    if match := HOLDER_RE.search(text):
        data["company_name"], data["city"] = match.group(1).strip(), match.group(2).strip()
    return data


def document_text(content: bytes, mime: str) -> str:
    """Text from a PDF, or OCR when the PDF is a scan or the file is a photo."""
    is_pdf = mime == "application/pdf" or content.startswith(b"%PDF")
    text = ""
    try:
        if is_pdf:
            text = _pdf_text(content)
            if len(re.sub(r"\s+", "", text)) < 80:
                text = _ocr_pdf(content) or text
        elif mime.startswith("image/"):
            text = _ocr_bytes(content)
    except Exception as exc:
        log.warning("Cannot read certificate file: %s", exc)
    return text


def read_certificate(content: bytes, mime: str) -> dict:
    """A text PDF is read directly. A photo, screenshot or scan is recognized as text."""
    is_pdf = mime == "application/pdf" or content.startswith(b"%PDF")
    text = ""
    try:
        if is_pdf:
            text = _pdf_text(content)
            if not _kvk_from_text(text):
                text = _ocr_pdf(content) or text
        elif mime.startswith("image/"):
            text = _ocr_bytes(content)
    except Exception as exc:
        log.warning("Cannot read SNA certificate: %s", exc)
        return _parse(text)
    return _parse(text)


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
