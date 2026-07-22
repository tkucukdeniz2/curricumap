# src/curricumap/synth.py
from __future__ import annotations
import numpy as np, pandas as pd
from .taxonomy import Taxonomy

def generate(tax: Taxonomy, n_students: int = 60, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a reproducible, messy synthetic transcript + catalog for a taxonomy.

    Each domain gets a few courses named after one of its rule patterns so the
    classifier maps them; injects retakes and sentinel zeros for realism.
    """
    rng = np.random.default_rng(seed)
    catalog = []
    for d in tax.domains:
        pats = next((r.patterns for r in tax.rules if r.domain == d.id), [d.label])
        for j in range(3):
            base = pats[j % len(pats)]
            catalog.append({"course_id": f"{d.id}_{j}",
                            "course_name": f"{base.title()} {j + 1}", "domain": d.id})
    catalog_df = pd.DataFrame(catalog)

    rows = []
    for sid in range(1, n_students + 1):
        ability = rng.normal(70, 10)
        for _, c in catalog_df.iterrows():
            if rng.random() < 0.1:            # 10% of enrollments missing
                continue
            grade = float(np.clip(rng.normal(ability, 8), 0, 100).round(0))
            rows.append({"student_id": sid, "course_id": c["course_id"],
                         "course_name": c["course_name"], "grade": grade})
            if rng.random() < 0.05:           # retake with a different grade
                g2 = float(np.clip(rng.normal(ability + 5, 8), 0, 100).round(0))
                rows.append({"student_id": sid, "course_id": c["course_id"],
                             "course_name": c["course_name"], "grade": g2})
            if rng.random() < 0.03:           # sentinel zero (non-attendance)
                rows.append({"student_id": sid, "course_id": c["course_id"],
                             "course_name": c["course_name"], "grade": 0.0})
    transcript = pd.DataFrame(rows)
    return transcript, catalog_df.drop(columns=["domain"])
