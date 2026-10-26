"""Course-to-domain classification with per-course provenance."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from rapidfuzz import fuzz

from .taxonomy import Taxonomy, normalize

_SCORERS = {"token_set_ratio": fuzz.token_set_ratio,
            "token_sort_ratio": fuzz.token_sort_ratio,
            "ratio": fuzz.ratio}

PROVENANCE_COLUMNS = ["course_id", "course_name", "domain", "method",
                      "pattern", "span", "score", "ambiguous", "n_titles"]


@dataclass(frozen=True)
class Assignment:
    domain: str | None
    method: str            # rule | override | fuzzy | unmatched
    pattern: str | None = None
    span: str | None = None
    score: float = 0.0
    ambiguous: bool = False


def _rule_hits(name_norm: str, tax: Taxonomy) -> list[tuple[str, str, str]]:
    """(domain, pattern, matched span) for every rule that matches, in rule order."""
    hits = []
    for domain, keywords, regexes in tax.compiled_rules:
        hit = next(((raw, kw) for raw, kw in keywords if kw in name_norm), None)
        if hit is None:
            hit = next(((raw, m.group(0)) for raw, rx in regexes
                        if (m := rx.search(name_norm))), None)
        if hit is not None:
            hits.append((domain, *hit))
    return hits


def _best_fuzzy(name_norm: str, tax: Taxonomy):
    scorer = _SCORERS[tax.fuzzy.scorer]
    best = (None, None, 0.0)
    for domain, keywords, _ in tax.compiled_rules:
        for raw, kw in keywords:
            s = scorer(name_norm, kw) / 100.0
            if s > best[2]:
                best = (domain, raw, s)
    return best


def assign_domain(course_name: str, tax: Taxonomy) -> Assignment:
    """Assign one course title: override, then ordered rules (first match wins), then fuzzy."""
    name_norm = normalize(course_name, tax.language)
    for ov in tax.overrides:
        if normalize(ov.course, tax.language) == name_norm:
            return Assignment(ov.domain, "override", score=1.0)
    hits = _rule_hits(name_norm, tax)
    if hits:
        domain, pattern, span = hits[0]
        return Assignment(domain, "rule", pattern=pattern, span=span, score=1.0,
                          ambiguous=len({d for d, _, _ in hits}) > 1)
    if tax.fuzzy.enabled:
        domain, pattern, score = _best_fuzzy(name_norm, tax)
        if domain is not None and score >= tax.fuzzy.threshold:
            return Assignment(domain, "fuzzy", pattern=pattern, span=pattern, score=round(score, 3))
    return Assignment(None, "unmatched")


def course_titles(courses: pd.DataFrame, tax: Taxonomy) -> pd.Series:
    """course_id -> the distinct titles printed under it, one rendering per normalised title."""
    pairs = courses[["course_id", "course_name"]].drop_duplicates()
    pairs = pairs.assign(_t=pairs["course_name"].astype(str).map(lambda s: normalize(s, tax.language)))
    return pairs.drop_duplicates(["course_id", "_t"]).groupby(
        "course_id", dropna=False, sort=False)["course_name"].agg(list)


def classify_courses(courses: pd.DataFrame, tax: Taxonomy) -> pd.DataFrame:
    """Provenance table: one row per distinct course_id, classified by its first title.

    `n_titles` counts the distinct normalised titles printed under the course_id; more
    than one means the code is shared by different courses.
    """
    n_titles = course_titles(courses, tax).map(len)
    rows = []
    for _, c in courses.drop_duplicates("course_id").iterrows():
        a = assign_domain(str(c["course_name"]), tax)
        rows.append({"course_id": c["course_id"], "course_name": c["course_name"],
                     "domain": a.domain, "method": a.method, "pattern": a.pattern,
                     "span": a.span, "score": a.score, "ambiguous": a.ambiguous,
                     "n_titles": int(n_titles.get(c["course_id"]))})
    return pd.DataFrame(rows, columns=PROVENANCE_COLUMNS)
