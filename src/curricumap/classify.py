# src/curricumap/classify.py
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .taxonomy import Taxonomy
from .text import normalize

@dataclass(frozen=True)
class Assignment:
    domain: str | None
    method: str            # rule | override | fuzzy | unmatched
    pattern: str | None = None
    span: str | None = None
    score: float = 0.0
    ambiguous: bool = False

def _matching_domains(name_norm: str, tax: Taxonomy) -> list[tuple[str, str]]:
    """Return (domain, pattern) for every rule whose pattern is a substring."""
    hits = []
    for rule in tax.rules:
        for pat in rule.patterns:
            if normalize(pat, tax.language) in name_norm:
                hits.append((rule.domain, pat))
                break
    return hits

def assign_domain(course_name: str, tax: Taxonomy) -> Assignment:
    name_norm = normalize(course_name, tax.language)
    for ov in tax.overrides:
        if normalize(ov.course, tax.language) == name_norm:
            return Assignment(ov.domain, "override", score=1.0)
    hits = _matching_domains(name_norm, tax)
    if hits:
        domain, pat = hits[0]                       # first match wins (rule order)
        ambiguous = len({d for d, _ in hits}) > 1
        return Assignment(domain, "rule", pattern=pat, span=pat, score=1.0, ambiguous=ambiguous)
    return Assignment(None, "unmatched")

def classify_courses(courses: pd.DataFrame, tax: Taxonomy) -> pd.DataFrame:
    rows = []
    for _, c in courses.drop_duplicates("course_id").iterrows():
        a = assign_domain(str(c["course_name"]), tax)
        rows.append({"course_id": c["course_id"], "course_name": c["course_name"],
                     "domain": a.domain, "method": a.method, "pattern": a.pattern,
                     "span": a.span, "score": a.score, "ambiguous": a.ambiguous})
    return pd.DataFrame(rows, columns=["course_id", "course_name", "domain",
                                       "method", "pattern", "span", "score", "ambiguous"])
