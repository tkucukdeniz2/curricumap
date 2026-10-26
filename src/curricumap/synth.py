"""Seeded, deliberately messy synthetic transcripts for any taxonomy (no real data involved)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .taxonomy import Taxonomy


def generate(tax: Taxonomy, n_students: int = 60, seed: int = 0,
             courses_per_domain: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a reproducible, messy synthetic transcript + catalog for a taxonomy.

    Each domain gets `courses_per_domain` courses named after the keywords of its
    first keyword rule, so the classifier maps them. Grades follow a one-factor
    model (student ability plus course noise); 10% of enrolments are missing, 5% are
    retaken with a second grade, and 3% carry an extra sentinel zero (non-attendance).
    """
    rng = np.random.default_rng(seed)
    catalog = []
    for d in tax.domains:
        pats = next((r.patterns for r in tax.rules if r.domain == d.id and r.patterns), [d.label])
        for j in range(courses_per_domain):
            catalog.append({"course_id": f"{d.id}_{j}",
                            "course_name": f"{pats[j % len(pats)]} {j + 1}", "domain": d.id})
    catalog_df = pd.DataFrame(catalog)

    rows = []
    for sid in range(1, n_students + 1):
        ability = rng.normal(70, 10)
        for j_idx, (_, c) in enumerate(catalog_df.iterrows()):
            if j_idx > 0 and rng.random() < 0.1:   # first course always kept; 10% of the rest missing
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
