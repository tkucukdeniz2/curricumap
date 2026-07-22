import re

def locale_casefold(s: str, language: str = "und") -> str:
    """Casefold that respects Turkish dotted/dotless i.

    For language == "tr": map İ→i and I→ı BEFORE casefold, so keyword
    matching is correct (naive casefold turns İ into i + combining dot).
    """
    if s is None:
        return ""
    if language == "tr":
        s = s.replace("İ", "i").replace("I", "ı")
    return s.casefold()

def normalize(s: str, language: str = "und") -> str:
    """Locale-casefold and collapse internal/edge whitespace."""
    return re.sub(r"\s+", " ", locale_casefold(s, language)).strip()
