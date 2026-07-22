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

def test_audit_alpha_uses_sentinel_dropped_data(tmp_path):
    tax = _tax(tmp_path)  # language_skills rule "okuma", pedagogy rule "öğretim"
    prov = pd.DataFrame({
        "course_id": ["c1", "c2", "c3", "p1"],
        "course_name": ["Okuma A", "Okuma B", "Okuma C", "Öğretim"],
        "domain": ["language_skills", "language_skills", "language_skills", "pedagogy"],
        "method": ["rule"] * 4, "pattern": ["okuma"] * 3 + ["öğretim"],
        "span": ["okuma"] * 3 + ["öğretim"], "score": [1.0] * 4, "ambiguous": [False] * 4,
    })
    rows = []
    grades = {1: (70, 72, 68), 2: (80, 82, 78), 3: (60, 61, 59),
              4: (90, 88, 92), 5: (50, 52, 48)}
    for sid, (a, b, c) in grades.items():
        rows += [(sid, "c1", "Okuma A", a), (sid, "c2", "Okuma B", b), (sid, "c3", "Okuma C", c)]
    rows.append((6, "c1", "Okuma A", 0))  # sentinel: sole record for student 6 on c1
    transcript = pd.DataFrame(rows, columns=["student_id", "course_id", "course_name", "grade"])
    wide = pd.DataFrame({"language_skills": [70.0, 80.0, 60.0, 90.0, 50.0, 0.0]},
                        index=pd.Index([1, 2, 3, 4, 5, 6], name="student_id"))
    cfg = {"prepare": {"sentinel_grades": {"values": [0], "action": "drop"},
                       "dedup": {"keep": "max"}}}
    data = run_audit(transcript, prov, wide, tax, cfg)
    clean = transcript[transcript.grade != 0]
    im = clean[clean.course_id.isin(["c1", "c2", "c3"])].pivot_table(
        index="student_id", columns="course_id", values="grade", aggfunc="max")
    exp_alpha, _ = cronbach_alpha(im, missing="column_mean")
    raw_im = transcript[transcript.course_id.isin(["c1", "c2", "c3"])].pivot_table(
        index="student_id", columns="course_id", values="grade", aggfunc="max")
    raw_alpha, _ = cronbach_alpha(raw_im, missing="column_mean")
    assert data["domains"]["language_skills"]["alpha"] == round(exp_alpha, 3)
    assert round(exp_alpha, 3) != round(raw_alpha, 3)  # sentinel really did matter
