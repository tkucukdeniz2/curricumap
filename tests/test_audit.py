import json
import re

import numpy as np
import pandas as pd
import pytest

from curricumap.audit import audit, cronbach_alpha, write_reports
from curricumap.classify import classify_courses


# --- Cronbach's alpha ----------------------------------------------------------------

def test_cronbach_alpha_of_parallel_items_is_one():
    m = pd.DataFrame({"i1": [2, 4, 3, 5], "i2": [1, 3, 2, 4], "i3": [3, 5, 4, 6]})
    assert cronbach_alpha(m) == (pytest.approx(1.0), 3)


def test_cronbach_alpha_matches_reference_value():
    m = pd.DataFrame({"i1": [4, 3, 5, 2, 4, 3], "i2": [5, 3, 4, 2, 5, 3],
                      "i3": [4, 2, 5, 3, 4, 2], "i4": [3, 3, 4, 1, 5, 2]})
    assert cronbach_alpha(m) == (pytest.approx(0.912158, abs=1e-6), 4)   # pingouin 0.7.0; Hoyt's ANOVA


# two students each miss one course grade
GAPPY = pd.DataFrame({"c1": [60, 70, 80, 90, np.nan, 75], "c2": [62, 68, 85, 88, 55, np.nan],
                      "c3": [58, 74, 79, 93, 50, 70]})


@pytest.mark.parametrize("missing, expected", [
    ("column_mean", 0.915581),   # gaps filled with the course mean: lowest
    ("listwise", 0.981379),      # the four complete students
    ("pairwise", 0.977024),      # each covariance from the students who have both grades
])
def test_cronbach_alpha_missing_grade_methods(missing, expected):
    assert cronbach_alpha(GAPPY, missing) == (pytest.approx(expected, abs=1e-6), 3)


def test_cronbach_alpha_rejects_unknown_missing_method():
    with pytest.raises(ValueError, match="pairwise"):
        cronbach_alpha(GAPPY, "colum_mean")


def test_pairwise_alpha_is_nan_when_two_items_share_no_student():
    m = pd.DataFrame({"i1": [1, 2, np.nan, np.nan], "i2": [np.nan, np.nan, 3, 4], "i3": [1, 2, 3, 4]})
    assert np.isnan(cronbach_alpha(m, "pairwise")[0])


def test_cronbach_alpha_needs_two_items():
    assert np.isnan(cronbach_alpha(pd.DataFrame({"i1": [1, 2, 3]}))[0])


# --- audit -----------------------------------------------------------------------------

def _transcript(rows):
    return pd.DataFrame(rows, columns=["student_id", "course_id", "course_name", "grade"])


ONE_STUDENT = _transcript([(1, "c1", "Okuma", 80.0), (1, "c2", "Matematik", 70.0)])
ONE_STUDENT_WIDE = pd.DataFrame({"language_skills": [80.0]}, index=pd.Index([1], name="student_id"))


def test_audit_reports_unmapped_and_domain_sizes(make_tax):
    tax = make_tax()
    data = audit(ONE_STUDENT, classify_courses(ONE_STUDENT, tax), ONE_STUDENT_WIDE, tax, {},
                 dropped={"sentinel": 0, "no_grade": 0, "retakes": 0, "low_coverage": 0})
    assert data["coverage"]["n_unmapped"] == 1
    assert data["coverage"]["unmapped_courses"] == ["Matematik"]
    assert data["coverage"]["domain_sizes"] == {"language_skills": 1, "pedagogy": 0}
    assert data["domains"]["language_skills"]["n_students"] == 1
    assert data["prepare"] == {"sentinel": 0, "no_grade": 0, "retakes": 0, "low_coverage": 0}


def test_uncomputable_statistics_are_null_not_nan(make_tax, tmp_path):
    tax = make_tax()
    data = audit(ONE_STUDENT, classify_courses(ONE_STUDENT, tax), ONE_STUDENT_WIDE, tax, {})
    ls, ped = data["domains"]["language_skills"], data["domains"]["pedagogy"]
    assert ls["mean"] == 80.0 and ls["sd"] is None and ls["skew"] is None   # one student
    assert ped["mean"] is None and ped["sd"] is None                       # no students
    assert ped["item_missing_pct"] == 0.0 and ped["n_complete"] == 0       # no items
    assert ped["missing_pct"] == 100.0 and ped["n_students"] == 0           # the matrix student lacks it
    write_reports(data, tmp_path)
    assert "NaN" not in (tmp_path / "audit.json").read_text("utf-8")
    html = (tmp_path / "audit.html").read_text("utf-8")
    assert ">nan<" not in html and ">None<" not in html


def test_audit_alpha_uses_cleaned_grades_of_matrix_students(make_tax):
    tax = make_tax()
    grades = {1: (70, 72, 68), 2: (80, 82, 78), 3: (60, 61, 59), 4: (90, 88, 92), 5: (50, 52, 48)}
    rows = [(s, f"c{i}", f"Okuma {i}", g) for s, gs in grades.items() for i, g in enumerate(gs, 1)]
    rows.append((6, "c1", "Okuma 1", 0))                  # sentinel: student 6's only record
    rows.append((7, "c1", "Okuma 1", 10))                 # student 7 is not in the delivered matrix
    t = _transcript(rows)
    wide = pd.DataFrame({"language_skills": [70.0, 80.0, 60.0, 90.0, 50.0]},
                        index=pd.Index([1, 2, 3, 4, 5], name="student_id"))
    cfg = {"prepare": {"sentinel_grades": {"values": [0], "action": "drop"}, "dedup": {"keep": "max"}}}
    data = audit(t, classify_courses(t, tax), wide, tax, cfg)
    items = t[t.student_id.between(1, 5)].pivot(index="student_id", columns="course_id", values="grade")
    assert data["domains"]["language_skills"]["alpha"] == round(cronbach_alpha(items)[0], 3)


def test_audit_reports_missing_grades_per_domain(make_tax):
    tax = make_tax()
    rows = [(s, f"c{i}", f"Okuma {i}", g) for s, gs in enumerate(GAPPY.to_numpy().tolist(), 1)
            for i, g in enumerate(gs, 1) if not np.isnan(g)]
    rows += [(1, "c4", "Okuma 4", 0), (7, "p1", "Öğretim 1", 80)]   # c4: a sentinel only; 7: no Okuma
    t = _transcript(rows)
    wide = pd.DataFrame({"language_skills": [70.0] * 6 + [np.nan], "pedagogy": [np.nan] * 6 + [80.0]},
                        index=pd.Index(range(1, 8), name="student_id"))
    # alpha rests on all 6 students with column_mean, on the 4 complete ones with listwise, and with
    # pairwise on 4: c1 and c2 are both graded for students 1-4 only
    for missing, alpha, n_alpha in (("column_mean", 0.916, 6), ("listwise", 0.981, 4),
                                    ("pairwise", 0.977, 4)):
        cfg = {"prepare": {"sentinel_grades": {"values": [0]}}, "audit": {"cronbach": {"missing": missing}}}
        data = audit(t, classify_courses(t, tax), wide, tax, cfg)
        ls = data["domains"]["language_skills"]
        assert data["cronbach_missing"] == missing and (ls["alpha"], ls["n_alpha"]) == (alpha, n_alpha)
        # 7 matrix students x 4 courses: two gaps, student 7 and the ungraded c4 -> 12 of 28 missing
        assert (ls["k"], ls["n_courses"], ls["item_missing_pct"], ls["n_complete"]) == (3, 4, 42.9, 0)


# --- reports ---------------------------------------------------------------------------

def _data(alpha=0.8, n_students=40, n_alpha=None, unmapped=()):
    return {"taxonomy": "t", "cronbach_missing": "column_mean",
            "coverage": {"n_unmapped": len(unmapped), "unmapped_courses": list(unmapped),
                         "n_ambiguous": 0, "n_title_conflicts": 0, "title_conflicts": [],
                         "domain_sizes": {"d1": 3}},
            "domains": {"d1": {"alpha": alpha, "k": 3, "n_courses": 3, "n_students": n_students,
                               "n_alpha": n_students if n_alpha is None else n_alpha,
                               "mean": 70.0, "sd": 5.0, "skew": 0.0, "missing_pct": 0.0,
                               "item_missing_pct": 4.2, "n_complete": 37}},
            "prepare": {"sentinel": 2, "no_grade": 0, "retakes": 5, "low_coverage": 1}}


def test_write_reports_creates_json_and_html(tmp_path):
    write_reports(_data(), tmp_path)
    assert json.loads((tmp_path / "audit.json").read_text("utf-8"))["domains"]["d1"]["alpha"] == 0.8
    html = (tmp_path / "audit.html").read_text("utf-8")
    assert "0.8" in html and "d1" in html and "width:80%" in html
    assert "<td>0.000</td>" in html                       # a real skew of 0.0 is shown, not blanked
    assert "<td>4.2</td>" in html and "missing grades %" in html
    assert 'Cronbach <span style="text-transform:none">α</span>' in html
    assert "dropped 2 sentinel grades, 5 retake records and 1 low-coverage student." in html
    assert "replaced by its course mean" in html
    assert "several titles" not in html


def test_report_html_escapes_course_names(tmp_path):
    write_reports(_data(unmapped=["Literature & <Composition>"]), tmp_path)
    html = (tmp_path / "audit.html").read_text("utf-8")
    assert "&amp;" in html and "&lt;Composition&gt;" in html
    assert "<Composition>" not in html


def test_negative_alpha_renders_an_empty_bar_and_a_note(tmp_path):
    # Rendering of a negative alpha such as the -0.36 in Reviewer 1's report (full scenario: test_cli.py)
    write_reports(_data(alpha=-0.36), tmp_path)
    html = (tmp_path / "audit.html").read_text("utf-8")
    widths = re.findall(r'<i style="width:(-?\d+)%">', html)
    assert widths == ["0"]
    assert "do not covary positively" in html


@pytest.mark.parametrize("n, n_alpha, alpha, band", [
    (5, 5, 0.75, "small"), (29, 29, 0.75, "small"), (30, 30, 0.75, "acc"), (5, 5, None, "na"),
    (60, 8, 0.99, "small"),   # e.g. listwise: 60 students take the domain, 8 have every grade
])
def test_alpha_of_fewer_than_30_students_is_grey_and_not_graded(tmp_path, n, n_alpha, alpha, band):
    write_reports(_data(alpha=alpha, n_students=n, n_alpha=n_alpha), tmp_path)
    html = (tmp_path / "audit.html").read_text("utf-8")
    assert f'<tr class="{band}">' in html
    assert ("<sup>‡</sup>Not graded" in html) == (band == "small")
    assert (f"= {n_alpha})" in html) == (n_alpha != n)    # the n behind alpha, when it is not the n column
