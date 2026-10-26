"""Coverage and reliability audit of a student-by-domain matrix, and its JSON/HTML report."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from .classify import course_titles
from .prepare import CRONBACH_MISSING, clean_grades, validate_config

_ENV = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=True)
MIN_STUDENTS_GRADED = 30   # below this many students behind alpha, the report shows it without a grade


def cronbach_alpha(item_matrix: pd.DataFrame, missing: str = "column_mean") -> tuple[float, int]:
    """Cronbach's alpha over a (respondents x items) matrix; k is the number of items (columns).

    Missing values are handled by `missing`: "column_mean" fills them with the item's
    mean, which shrinks the covariances and so biases alpha downward as missingness
    grows; "listwise" keeps only complete rows; "pairwise" estimates each covariance
    from the rows that have both items. Returns (nan, k) when alpha is not computable:
    fewer than 2 items or rows, zero total variance, or (pairwise) a pair of items
    shared by fewer than 2 rows.
    """
    if missing not in CRONBACH_MISSING:
        raise ValueError(f"audit.cronbach.missing must be one of {CRONBACH_MISSING}, got {missing!r}")
    m = item_matrix
    if missing == "column_mean":
        m = m.fillna(m.mean(axis=0))
    if missing != "pairwise":
        m = m.dropna(axis=0, how="any")
    k = m.shape[1]
    if k < 2 or m.shape[0] < 2:
        return (float("nan"), k)
    c = m.cov(min_periods=2).to_numpy()
    if np.isnan(c).any() or c.sum() == 0:
        return (float("nan"), k)
    return (float((k / (k - 1)) * (1 - np.trace(c) / c.sum())), k)


def _finite(x, ndigits: int) -> float | None:
    """x rounded, or None when it is not finite (SD of one student, skew of fewer than three)."""
    x = float(x)
    return round(x, ndigits) if math.isfinite(x) else None


def audit(transcript, provenance, wide, tax, config, dropped: dict | None = None) -> dict:
    """Coverage of the classification and per-domain descriptives and Cronbach's alpha.

    Alpha uses the course grades (items) of each domain for the students in the
    delivered matrix, after the same cleaning that built it (sentinel and no-grade records
    dropped, retakes merged).
    `dropped` (PrepareResult.dropped, what cleaning removed) is reported as "prepare".
    """
    prov = provenance
    unmapped = prov[prov["domain"].isna()]
    codes = prov.loc[prov["n_titles"] > 1, "course_id"]
    shared = course_titles(transcript[transcript["course_id"].isin(codes)], tax)   # codes with several titles
    course_domain = prov.dropna(subset=["domain"]).set_index("course_id")["domain"]
    missing = validate_config(config)["missing"]
    grades = clean_grades(transcript, config)
    grades = grades[grades["student_id"].isin(wide.index)]

    domains = {}
    for d in tax.domains:
        course_ids = course_domain[course_domain == d.id].index
        items = grades[grades["course_id"].isin(course_ids)].pivot_table(
            index="student_id", columns="course_id", values="grade", aggfunc="mean")
        alpha, k = cronbach_alpha(items, missing)
        seen = items.notna().to_numpy(dtype=int)
        full = items.reindex(index=wide.index, columns=course_ids)   # every matrix student x every course
        # a domain no matrix student has is missing for all of them
        col = wide[d.id] if d.id in wide.columns else pd.Series(float("nan"), index=wide.index, dtype=float)
        domains[d.id] = {
            "alpha": _finite(alpha, 3), "k": int(k),
            "n_courses": int(len(course_ids)),
            "n_students": int(col.notna().sum()),
            # students behind alpha; for pairwise, the fewest that share two of the courses
            "n_alpha": {"column_mean": len(items), "listwise": int(seen.all(axis=1).sum()),
                        "pairwise": int((seen.T @ seen).min()) if seen.size else 0}[missing],
            "mean": _finite(col.mean(), 2),
            "sd": _finite(col.std(ddof=1), 2),
            "skew": _finite(col.skew(), 3),
            "missing_pct": 0.0 if col.empty else round(float(col.isna().mean() * 100), 1),
            "item_missing_pct": round(float(full.isna().to_numpy().mean() * 100), 1) if full.size else 0.0,
            "n_complete": int(full.notna().all(axis=1).sum()) if full.size else 0,
        }
    return {
        "taxonomy": tax.id,
        "cronbach_missing": missing,
        "coverage": {
            "n_unmapped": int(len(unmapped)),
            "unmapped_courses": sorted(unmapped["course_name"].astype(str).unique().tolist()),
            "n_ambiguous": int(prov["ambiguous"].sum()),
            "n_title_conflicts": len(shared),
            "title_conflicts": [{"course_id": str(c), "titles": sorted(map(str, t))}
                                for c, t in sorted(shared.items(), key=lambda ct: str(ct[0]))],
            "domain_sizes": {d.id: domains[d.id]["n_courses"] for d in tax.domains},
        },
        "domains": domains,
        "prepare": dropped,
    }


def write_reports(audit_data: dict, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(audit_data, indent=2, ensure_ascii=False, allow_nan=False),
                                    "utf-8")
    html = _ENV.get_template("audit.html.j2").render(a=audit_data, min_n=MIN_STUDENTS_GRADED)
    (out / "audit.html").write_text(html, "utf-8")
