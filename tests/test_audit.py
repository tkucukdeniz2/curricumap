# tests/test_audit.py
import numpy as np, pandas as pd
from curricumap.audit import cronbach_alpha
from curricumap.audit import audit as run_audit
from curricumap.taxonomy import load_taxonomy

def test_cronbach_alpha_matches_hand_computation():
    # 3 items, 4 respondents; alpha = (k/(k-1))*(1 - sum(item_var)/total_var)
    m = pd.DataFrame({"i1": [2, 4, 3, 5], "i2": [1, 3, 2, 4], "i3": [3, 5, 4, 6]})
    k = m.shape[1]
    item_var = m.var(ddof=1).sum()
    total_var = m.sum(axis=1).var(ddof=1)
    expected = (k / (k - 1)) * (1 - item_var / total_var)
    alpha, kk = cronbach_alpha(m)
    assert kk == 3
    assert abs(alpha - expected) < 1e-9

def test_cronbach_alpha_imputes_column_mean_for_missing():
    m = pd.DataFrame({"i1": [2, 4, np.nan, 5], "i2": [1, 3, 2, 4], "i3": [3, 5, 4, 6]})
    alpha, k = cronbach_alpha(m, missing="column_mean")
    assert not np.isnan(alpha)
    assert k == 3

def _tax(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("""
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: language_skills, label: LS}, {id: pedagogy, label: Ped}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: ratio } }
  rules: [{domain: language_skills, any: ["okuma"]}, {domain: pedagogy, any: ["öğretim"]}]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    return load_taxonomy(p)

def test_audit_reports_unmapped_and_domain_sizes(tmp_path):
    transcript = pd.DataFrame({"student_id": [1, 1], "course_id": ["c1", "c2"],
                               "course_name": ["Okuma", "Matematik"], "grade": [80.0, 70.0]})
    prov = pd.DataFrame({"course_id": ["c1", "c2"], "course_name": ["Okuma", "Matematik"],
                         "domain": ["language_skills", None], "method": ["rule", "unmatched"],
                         "pattern": ["okuma", None], "span": ["okuma", None],
                         "score": [1.0, 0.0], "ambiguous": [False, False]})
    wide = pd.DataFrame({"language_skills": [80.0]}, index=pd.Index([1], name="student_id"))
    data = run_audit(transcript, prov, wide, _tax(tmp_path), {})
    assert data["coverage"]["n_unmapped"] == 1
    assert "Matematik" in data["coverage"]["unmapped_courses"]
    assert data["domains"]["language_skills"]["n_students"] == 1
