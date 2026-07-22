# tests/test_classify.py
import pandas as pd
from curricumap.taxonomy import load_taxonomy
from curricumap.classify import assign_domain, classify_courses

def _tax(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("""
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: literature, label: Lit}, {id: pedagogy, label: Ped}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: token_set_ratio } }
  rules:
    - { domain: literature, any: ["edebiyat", "literature"] }
    - { domain: pedagogy, any: ["öğretim", "teaching"] }
  overrides: [{ course: "Özel Ders", domain: pedagogy }]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    return load_taxonomy(p)

def test_rule_match_records_method_and_pattern(tmp_path):
    a = assign_domain("İngiliz Edebiyatı", _tax(tmp_path))
    assert a.domain == "literature"
    assert a.method == "rule"
    assert a.pattern == "edebiyat"

def test_override_beats_rule(tmp_path):
    a = assign_domain("Özel Ders", _tax(tmp_path))
    assert a.domain == "pedagogy"
    assert a.method == "override"

def test_unmatched_is_flagged(tmp_path):
    a = assign_domain("Matematik", _tax(tmp_path))
    assert a.domain is None
    assert a.method == "unmatched"

def test_classify_courses_returns_provenance_table(tmp_path):
    courses = pd.DataFrame({"course_id": ["c1", "c2"],
                            "course_name": ["Edebiyat", "Matematik"]})
    prov = classify_courses(courses, _tax(tmp_path))
    assert list(prov.columns) == ["course_id", "course_name", "domain",
                                  "method", "pattern", "span", "score", "ambiguous"]
    assert prov.loc[prov.course_id == "c1", "domain"].item() == "literature"

from curricumap.taxonomy import load_taxonomy as _lt
from curricumap.classify import assign_domain as _ad

def _fuzzy_tax(tmp_path):
    p = tmp_path / "fz.yaml"
    p.write_text("""
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: literature, label: Lit}]
  match: { strategy: ordered_rules, fuzzy: { enabled: true, threshold: 0.80, scorer: token_set_ratio } }
  rules: [{ domain: literature, any: ["ingiliz edebiyati"] }]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    return _lt(p)

def test_fuzzy_matches_near_variant(tmp_path):
    a = _ad("İngiliz Edebiyatı I", _fuzzy_tax(tmp_path))   # near "ingiliz edebiyati"
    assert a.domain == "literature"
    assert a.method == "fuzzy"
    assert a.score >= 0.80

def test_fuzzy_below_threshold_stays_unmatched(tmp_path):
    a = _ad("Diferansiyel Denklemler", _fuzzy_tax(tmp_path))
    assert a.domain is None
    assert a.method == "unmatched"
