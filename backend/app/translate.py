import json
import urllib.parse
import urllib.request

def to_dutch(text: str) -> str:
    source = (text or "").strip()
    if not source or not any("\u0400" <= char <= "\u04ff" for char in source):
        return source
    parts = []
    rest = source
    while rest:
        chunk = rest[:400]
        if len(rest) > 400:
            split = max(chunk.rfind("\n"), chunk.rfind(". "), chunk.rfind(" "))
            if split > 80:
                chunk = rest[: split + 1]
        rest = rest[len(chunk) :]
        parts.append(_translate_chunk(chunk.strip(), _pairs(source)) or chunk.strip())
    return "\n".join(part for part in parts if part).strip() or source


def _pairs(text: str) -> tuple[str, ...]:
    lower = text.lower()
    if any(char in lower for char in "іїєґ"):
        return ("uk|nl",)
    if any(char in lower for char in "ыэъё"):
        return ("ru|nl",)
    return ("uk|nl", "ru|nl")


def _translate_chunk(text: str, pairs: tuple[str, ...]) -> str:
    for pair in pairs:
        query = urllib.parse.urlencode({"q": text, "langpair": pair})
        try:
            with urllib.request.urlopen(
                f"https://api.mymemory.translated.net/get?{query}", timeout=8
            ) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
        except Exception:
            continue
        translated = ((payload.get("responseData") or {}).get("translatedText") or "").strip()
        if translated and "MYMEMORY WARNING" not in translated.upper() and translated.lower() != text.lower():
            return translated
    return ""
