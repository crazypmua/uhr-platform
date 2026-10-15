"""ISO 9001 guess: certificates differ by issuer, so this only reads the file and estimates."""
import re
from datetime import datetime, timezone

from .sna import _kvk_from_text, document_text

ISO9001_RE = re.compile(r"iso[\s\-]*9001(?:\s*[:/]\s*20\d{2})?", re.I)
OTHER_ISO_RE = re.compile(r"iso[\s\-]*(14001|45001|27001|22000|50001)(?:\s*[:/]\s*20\d{2})?", re.I)
CERT_RE = re.compile(r"certificaat|certificate|zertifikat|certificat", re.I)
QUALITY_RE = re.compile(r"kwaliteitsmanagement|quality management|managementsysteem|quality system", re.I)
NAME_RE = re.compile(
    r"(?:this is to certify that|hierbij wordt verklaard dat|certificaat(?:houder)?|granted to|issued to|awarded to|afgegeven aan|organisatie|organization)\s*[:\n]?\s*([A-Z0-9][^\n]{2,80})",
    re.I,
)
NUMBER_RE = re.compile(
    r"(?:certificate\s*(?:no\.?|number|nr\.?)|certificaat(?:nummer)?|registration\s*(?:no\.?|number))\s*[:\s#]*([A-Z0-9][A-Z0-9\-/]{3,30})",
    re.I,
)
UNTIL_RE = re.compile(
    r"(?:valid until|geldig tot|expiry date|expires|vervaldatum|expir(?:y|es))\s*[:\s]*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
    re.I,
)
ISSUERS = (
    ("bureau veritas", "Bureau Veritas"),
    ("kiwa", "Kiwa"),
    ("dekra", "DEKRA"),
    ("lrqa", "LRQA"),
    ("lloyd", "Lloyd's Register"),
    ("dnv", "DNV"),
    ("tüv", "TÜV"),
    ("tuv", "TÜV"),
    ("sgs", "SGS"),
    ("bsi", "BSI"),
    ("nqa", "NQA"),
    ("sccm", "SCCM"),
    ("vincotte", "Vinçotte"),
    ("vinçotte", "Vinçotte"),
    ("intertek", "Intertek"),
    ("dqs", "DQS"),
)


def _clean_name(value: str) -> str:
    name = re.sub(r"\s+", " ", value).strip(" .:-")
    if not name or ISO9001_RE.search(name) or len(name) < 3:
        return ""
    return name[:80]


def guess_text(text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", text or "")
    lower = flat.lower()
    found = ISO9001_RE.search(flat)
    others = []
    for match in OTHER_ISO_RE.finditer(flat):
        label = re.sub(r"\s+", " ", match.group(0)).upper().replace("ISO-", "ISO ")
        if label not in others:
            others.append(label)
    standard = ""
    if found:
        standard = re.sub(r"\s+", " ", found.group(0)).upper().replace("ISO-", "ISO ")
        guess, confidence = "iso9001", "high"
    elif QUALITY_RE.search(flat) and CERT_RE.search(flat):
        guess, confidence = "iso9001", "medium"
    elif others:
        guess, confidence = "other_iso", "medium"
    elif "iso" in lower or CERT_RE.search(flat):
        guess, confidence = "unknown", "low"
    else:
        guess, confidence = "unknown", "low"
    issuer = next((label for needle, label in ISSUERS if needle in lower), "")
    company = ""
    if match := NAME_RE.search(text or ""):
        company = _clean_name(match.group(1))
    number = NUMBER_RE.search(flat)
    until = UNTIL_RE.search(flat)
    kvk = _kvk_from_text(text or "")
    return {
        "kind": "iso",
        "guess": guess,
        "confidence": confidence,
        "standard": standard,
        "standards": others,
        "issuer": issuer,
        "company_name": company,
        "kvk": kvk,
        "certificate_number": number.group(1) if number else "",
        "valid_until": until.group(1) if until else "",
        "excerpt": re.sub(r"\s+", " ", flat).strip()[:400],
    }


def check_certificate(content: bytes, mime: str) -> dict:
    read = guess_text(document_text(content, mime))
    return {
        "kind": "iso",
        "guess": read["guess"],
        "confidence": read["confidence"],
        "standards": read["standards"],
        "kvk": read["kvk"],
        "verified": read["guess"] == "iso9001" and read["confidence"] == "high",
        "extracted": {
            "standard": read["standard"],
            "issuer": read["issuer"],
            "company_name": read["company_name"],
            "kvk": read["kvk"],
            "certificate_number": read["certificate_number"],
            "valid_until": read["valid_until"],
            "excerpt": read["excerpt"],
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
