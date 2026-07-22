# tests/test_prepare.py
import pandas as pd
from curricumap.prepare import prepare
from curricumap.prepare import reconstruct_study_year

def _prov():
    return pd.DataFrame({
        "course_id": ["c1", "c2", "c3"],
        "course_name": ["Okuma", "Yazma", "Öğretim"],
        "domain": ["language_skills", "language_skills", "pedagogy"],
    })

def _transcript():
    # student 1 retook c1 (50 then 80 -> keep max 80); a sentinel 0 on c3
    return pd.DataFrame({
        "student_id": [1, 1, 1, 1, 2, 2],
        "course_id": ["c1", "c1", "c2", "c3", "c1", "c3"],
        "course_name": ["Okuma", "Okuma", "Yazma", "Öğretim", "Okuma", "Öğretim"],
        "grade": [50, 80, 70, 0, 60, 90],
    })

CFG = {"prepare": {"dedup": {"on": ["student_id", "course_id"], "keep": "max"},
                   "sentinel_grades": {"values": [0], "action": "drop"},
                   "coverage": {"min_domains": 1},
                   "aggregate": {"method": "mean"}}}

def test_dedup_keeps_max_grade():
    res = prepare(_transcript(), _prov(), CFG)
    # student 1 language_skills = mean(max(c1)=80, c2=70) = 75
    assert res.wide.loc[1, "language_skills"] == 75.0

def test_sentinel_zero_dropped_from_domain_mean():
    res = prepare(_transcript(), _prov(), CFG)
    # student 1 pedagogy came only from c3=0 which is dropped -> NaN
    assert pd.isna(res.wide.loc[1, "pedagogy"])
    # student 2 pedagogy = 90
    assert res.wide.loc[2, "pedagogy"] == 90.0

def test_coverage_filter_drops_students_below_min_domains():
    cfg = {"prepare": {**CFG["prepare"], "coverage": {"min_domains": 2}}}
    res = prepare(_transcript(), _prov(), cfg)
    # student 1's only pedagogy grade (c3=0) is a sentinel and is dropped, so
    # student 1 covers just language_skills (1 domain) -> filtered out;
    # student 2 covers language_skills(=60) and pedagogy(=90) => 2 domains -> kept.
    assert 1 not in res.wide.index
    assert 2 in res.wide.index

def test_study_year_from_dates():
    dates = pd.to_datetime(["2019-11-01", "2020-05-01", "2022-11-01"])
    enroll = pd.Series([2019, 2019, 2019])
    yrs = reconstruct_study_year(pd.Series(dates), enroll, term_boundary="09-01", max_year=4)
    # 2019-11 fall of enrollment year -> year 1; 2020-05 -> still year 1 (spring); 2022-11 -> year 4
    assert yrs.tolist() == [1, 1, 4]

def test_study_year_clipped_to_max():
    dates = pd.to_datetime(["2030-11-01"])
    yrs = reconstruct_study_year(pd.Series(dates), pd.Series([2019]),
                                 term_boundary="09-01", max_year=4)
    assert yrs.tolist() == [4]
