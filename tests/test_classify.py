import pandas as pd

from curricumap.classify import PROVENANCE_COLUMNS, assign_domain, classify_courses

SPEC = """
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: literature, label: Lit}, {id: linguistics, label: Ling}, {id: pedagogy, label: Ped}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false } }
  rules:
    - { domain: literature, any: ["edebiyat", "literature"] }
    - { domain: linguistics, any: ["dilbilim"], regex: ['\\bdil edinimi\\b'] }
    - { domain: pedagogy, any: ["öğretim", "teaching"] }
  overrides: [{ course: "Özel Ders", domain: pedagogy }]
"""

FUZZY = """
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: literature, label: Lit}]
  match: { strategy: ordered_rules, fuzzy: { enabled: true, threshold: 0.80, scorer: token_set_ratio } }
  rules: [{ domain: literature, any: ["ingiliz edebiyati"] }]
"""


def test_rule_match_records_method_and_pattern(make_tax):
    a = assign_domain("İngiliz Edebiyatı", make_tax(SPEC))
    assert (a.domain, a.method, a.pattern) == ("literature", "rule", "edebiyat")


def test_keywords_match_turkish_uppercase_registrar_titles(make_tax):
    assert assign_domain("DİLBİLİMİ 1", make_tax(SPEC)).domain == "linguistics"


def test_regex_rule_records_pattern_and_matched_span(make_tax):
    a = assign_domain("DİL EDİNİMİ", make_tax(SPEC))
    assert (a.domain, a.method) == ("linguistics", "rule")
    assert a.pattern == r"\bdil edinimi\b"
    assert a.span == "dil edinimi"


def test_first_match_wins_and_ambiguity_is_flagged(make_tax):
    a = assign_domain("Dil ve Edebiyat Öğretimi", make_tax(SPEC))  # literature and pedagogy
    assert a.domain == "literature"
    assert a.ambiguous is True
    assert assign_domain("Dilbilime Giriş", make_tax(SPEC)).ambiguous is False


def test_override_beats_rule(make_tax):
    a = assign_domain("ÖZEL DERS", make_tax(SPEC))
    assert (a.domain, a.method) == ("pedagogy", "override")


def test_unmatched_is_flagged(make_tax):
    a = assign_domain("Matematik", make_tax(SPEC))
    assert (a.domain, a.method) == (None, "unmatched")


def test_classify_courses_returns_provenance_table(make_tax):
    courses = pd.DataFrame({"course_id": ["c1", "c2", "c1"],
                            "course_name": ["Edebiyat", "Matematik", "Edebiyat"]})
    prov = classify_courses(courses, make_tax(SPEC))
    assert list(prov.columns) == PROVENANCE_COLUMNS
    assert len(prov) == 2
    assert prov.loc[prov.course_id == "c1", "domain"].item() == "literature"


def test_course_code_shared_by_different_titles_is_counted(make_tax):
    courses = pd.DataFrame({"course_id": ["c1", "c1", "c1", "c2"],
                            "course_name": ["Edebiyat", "EDEBİYAT", "Dilbilime Giriş", "Matematik"]})
    prov = classify_courses(courses, make_tax(SPEC)).set_index("course_id")
    assert prov["n_titles"].to_dict() == {"c1": 2, "c2": 1}    # case variants are one title
    assert prov.loc["c1", "domain"] == "literature"             # classified by its first title


def test_fuzzy_matches_near_variant(make_tax):
    a = assign_domain("İngiliz Edebiyatı I", make_tax(FUZZY))  # near "ingiliz edebiyati"
    assert (a.domain, a.method) == ("literature", "fuzzy")
    assert a.score >= 0.80


def test_fuzzy_below_threshold_stays_unmatched(make_tax):
    a = assign_domain("Diferansiyel Denklemler", make_tax(FUZZY))
    assert (a.domain, a.method) == (None, "unmatched")
