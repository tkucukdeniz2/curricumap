# src/curricumap/audit.py
from __future__ import annotations
import pandas as pd

def cronbach_alpha(item_matrix: pd.DataFrame, missing: str = "column_mean") -> tuple[float, int]:
    """Cronbach's alpha over an (respondents x items) matrix.

    `missing == "column_mean"` fills NaNs with each item's mean; k is the
    number of items (columns). Returns (nan, k) if fewer than 2 items.
    """
    m = item_matrix.copy()
    if missing == "column_mean":
        m = m.fillna(m.mean(axis=0))
    m = m.dropna(axis=0, how="any")
    k = m.shape[1]
    if k < 2 or m.shape[0] < 2:
        return (float("nan"), k)
    item_var = m.var(axis=0, ddof=1).sum()
    total_var = m.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return (float("nan"), k)
    alpha = (k / (k - 1)) * (1 - item_var / total_var)
    return (float(alpha), k)

def audit(transcript, provenance, wide, tax, config) -> dict:
    prov = provenance
    unmapped_rows = prov[prov["domain"].isna()]
    n_unmapped = int(len(unmapped_rows))
    unmapped = sorted(unmapped_rows["course_name"].astype(str).unique().tolist())
    n_ambiguous = int(prov["ambiguous"].sum()) if "ambiguous" in prov else 0
    course_domain = prov.dropna(subset=["domain"]).set_index("course_id")["domain"]

    # Clean the transcript with the SAME sentinel/dedup policy prepare() applies,
    # so Cronbach's alpha describes the same data as the output matrix.
    pcfg = config.get("prepare", {})
    t = transcript.copy()
    sent = pcfg.get("sentinel_grades", {})
    if sent.get("action") == "drop" and sent.get("values"):
        t = t[~t["grade"].isin(sent["values"])]
    keep = pcfg.get("dedup", {}).get("keep", "max")
    aggfunc = {"max": "max", "last": "last", "mean": "mean"}.get(keep, "max")

    domains = {}
    miss_cfg = config.get("audit", {}).get("cronbach", {}).get("missing", "column_mean")
    for d in tax.domains:
        course_ids = course_domain[course_domain == d.id].index
        sub = t[t["course_id"].isin(course_ids)]
        item_matrix = sub.pivot_table(index="student_id", columns="course_id",
                                      values="grade", aggfunc=aggfunc)
        alpha, k = cronbach_alpha(item_matrix, missing=miss_cfg) if item_matrix.shape[1] >= 2 else (float("nan"), item_matrix.shape[1])
        col = wide[d.id] if d.id in wide.columns else pd.Series(dtype=float)
        domains[d.id] = {
            "alpha": None if pd.isna(alpha) else round(alpha, 3), "k": int(k),
            "n_courses": int(len(course_ids)),
            "n_students": int(col.notna().sum()),
            "mean": None if col.empty else round(float(col.mean()), 2),
            "sd": None if col.empty else round(float(col.std(ddof=1)), 2),
            "skew": None if col.empty else round(float(col.skew()), 3),
            "missing_pct": 0.0 if col.empty else round(float(col.isna().mean() * 100), 1),
        }
    return {
        "taxonomy": tax.id,
        "coverage": {
            "n_unmapped": n_unmapped, "unmapped_courses": unmapped,
            "n_ambiguous": n_ambiguous,
            "domain_sizes": {d.id: domains[d.id]["n_courses"] for d in tax.domains},
        },
        "domains": domains,
    }
