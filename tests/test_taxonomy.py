import copy
import csv
from pathlib import Path

import pytest

from curricumap.classify import assign_domain, classify_courses
from curricumap.synth import generate
from curricumap.taxonomy import (bundled_taxonomies, load_taxonomy, locale_casefold, normalize,
                                 validate_taxonomy)

VALIDATION_DATA = Path(__file__).resolve().parents[1] / "validation" / "data"

VALID = {
    "taxonomy": {
        "id": "t1", "label": "T1",
        "locale": {"language": "tr", "casefold": "locale-aware"},
        "domains": [{"id": "d1", "label": "D1"}, {"id": "d2", "label": "D2"}],
        "match": {"strategy": "ordered_rules",
                  "fuzzy": {"enabled": True, "threshold": 0.88, "scorer": "token_set_ratio"}},
        "rules": [{"domain": "d1", "any": ["okuma"]}, {"domain": "d2", "regex": [r"^öğretim\b"]}],
        "overrides": [{"course": "X", "domain": "d1"}],
        "defaults": {"unmatched": "flag"},
    }
}


def _with(**changes):
    spec = copy.deepcopy(VALID)
    spec["taxonomy"].update(changes)
    return spec


# --- locale-aware text matching -------------------------------------------------

def test_turkish_dotted_capital_i_becomes_plain_i():
    # naive .casefold() gives "i̇ngilizce" (i + combining dot); locale must give "ingilizce"
    assert locale_casefold("İngilizce", "tr") == "ingilizce"
    assert "İngilizce".casefold() != "ingilizce"  # proves the naive path is wrong


def test_turkish_dotless_capital_i_becomes_dotless():
    assert locale_casefold("ISI", "tr") == "ısı"
    assert "ISI".lower() == "isi"  # proves the naive path is wrong


def test_decomposed_and_naively_lowered_turkish_text_is_normalised():
    assert locale_casefold("I\u0307NG\u0130L\u0130ZCE", "tr") == "ingilizce"   # NFD capital İ
    assert locale_casefold("di\u0307lbi\u0307li\u0307mi\u0307 1", "tr") == "dilbilimi 1"  # str.lower() output


@pytest.mark.parametrize("language", ["tr", "TR", "tr-TR", "tr_TR", "tur"])
def test_any_form_of_the_turkish_tag_turns_on_turkish_folding(language):
    assert locale_casefold("İNGİLİZ EDEBİYATI I", language) == "ingiliz edebiyatı ı"


def test_default_language_uses_standard_casefold():
    assert locale_casefold("READING", "und") == "reading"


def test_normalize_collapses_whitespace_and_casefolds():
    assert normalize("  Öğretim   Yöntemleri ", "tr") == "öğretim yöntemleri"


# --- schema and cross-checks -----------------------------------------------------

def test_validate_accepts_valid_spec():
    assert validate_taxonomy(VALID) == []


@pytest.mark.parametrize("changes, fragment", [
    ({"rules": [{"domain": "nope", "any": ["x"]}]}, "nope"),
    ({"rules": [{"domain": "d1", "regex": ["("]}]}, "invalid regex"),
    ({"rules": [{"domain": "d1", "any": [""]}]}, "rules/0/any/0"),
    ({"rules": [{"domain": "d1"}]}, "valid under any"),
    ({"defaults": {"unmatched": "d1"}}, "flag"),
    ({"overrides": [{"course": "X", "domain": "nope"}]}, "nope"),
    # misspelled keys are rejected, not silently ignored
    ({"overides": [{"course": "X", "domain": "d1"}]}, "'overides' was unexpected"),
    ({"rules": [{"domain": "d1", "regexes": ["^x"]}]}, "'regexes' was unexpected"),
    ({"locale": {"lang": "tr"}}, "'lang' was unexpected"),
    ({"locale": {"language": "tr", "casefold": "none"}}, "locale/casefold"),
    ({"match": {"fuzy": {"enabled": True}}}, "'fuzy' was unexpected"),
    ({"defualts": {"unmatched": "flag"}}, "'defualts' was unexpected"),
])
def test_validate_rejects_invalid_specs(changes, fragment):
    errors = validate_taxonomy(_with(**changes))
    assert any(fragment in e for e in errors), errors


@pytest.mark.parametrize("changes", [
    {"rules": ["edebiyat"]}, {"domains": {"d1": "D1"}}, {"overrides": {"X": "d1"}},
    {"rules": [{"domain": "d1", "regex": r"\bs[ıi]n[ıi]f\b"}]},   # a string, not a list of regexes
])
def test_malformed_spec_gives_its_schema_error_not_a_crash(changes):
    errors = validate_taxonomy(_with(**changes))
    assert len(errors) == 1 and "is not of type" in errors[0], errors


def test_load_taxonomy_keeps_its_v01_keyword(spec_path):
    assert load_taxonomy(path=spec_path()).id == "t"      # the argument is still called path


def test_load_taxonomy_from_yaml(make_tax):
    tax = make_tax()
    assert tax.id == "t"
    assert tax.language == "tr"
    assert [d.id for d in tax.domains] == ["language_skills", "pedagogy"]
    assert tax.rules[0].patterns == ["okuma"]
    assert tax.fuzzy.enabled is False


def test_invalid_spec_raises_on_load(spec_path):
    p = spec_path("taxonomy: {id: t, label: T, domains: [], rules: []}\n")
    with pytest.raises(ValueError, match="Invalid taxonomy"):
        load_taxonomy(p)


# --- bundled taxonomies -------------------------------------------------------------

def test_bundled_taxonomies_are_listed():
    assert set(bundled_taxonomies()) >= {"bologna", "canmeds", "elt_yok_2018",
                                         "engineering_mudek", "math_ed_yok"}


@pytest.mark.parametrize("ref", ["elt_yok_2018", "elt_yok_2018.yaml"])
def test_bundled_taxonomy_loads_by_name(ref, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no such file here, so the bundled copy is used
    assert load_taxonomy(ref).id == "elt_yok_2018"


def test_unknown_taxonomy_name_lists_bundled():
    with pytest.raises(FileNotFoundError, match="elt_yok_2018"):
        load_taxonomy("no_such_taxonomy")


@pytest.mark.parametrize("name", sorted(bundled_taxonomies()))
def test_every_bundled_taxonomy_classifies_its_synthetic_courses(name):
    tax = load_taxonomy(name)
    _, catalog = generate(tax, n_students=30, seed=7)
    prov = classify_courses(catalog, tax)
    expected = catalog["course_id"].str.rsplit("_", n=1).str[0]
    assert (prov["domain"] == expected).all(), prov[prov["domain"] != expected]


# --- the bundled ELT taxonomy keeps its validated results -----------------------------
# Statement coverage cannot reach the rules of a YAML file, so these tests pin what the
# ELT taxonomy does: an edit that changes a validated result must fail here.

@pytest.fixture(scope="module")
def elt():
    return load_taxonomy("elt_yok_2018")


@pytest.mark.parametrize("name, correct, ambiguous, misses", [
    ("iuc_elt_catalog.csv", 143, 10, []),
    # the one known miss: the 2006 programme lists "Türk Eğitim Tarihi" as general culture
    ("yok_programmes.csv", 157, 14, [("Türk Eğitim Tarihi", "general_ed", "pedagogy")]),
])
def test_elt_taxonomy_reproduces_the_validation(elt, name, correct, ambiguous, misses):
    with open(VALIDATION_DATA / name, encoding="utf-8", newline="") as fh:
        rows = [(r["title"], r["domain"]) for r in csv.DictReader(fh)]
    got = [assign_domain(title, elt) for title, _ in rows]
    assert [(t, d, a.domain) for (t, d), a in zip(rows, got) if a.domain != d] == misses
    assert len(rows) - len(misses) == correct
    assert sum(a.domain is None for a in got) == 0
    assert sum(a.ambiguous for a in got) == ambiguous


# Registrar renderings documented in the comments of elt_yok_2018.yaml (abbreviations,
# ASCII spellings, synonyms) and titles it deliberately leaves unmatched (None).
@pytest.mark.parametrize("title, domain", [
    ("YAB. DİL II", "general_ed"), ("TURK DILI I", "general_ed"),
    ("MESLEKİ İNG.", "general_ed"), ("GELENEKSEL TÜRK EL SAN.", "general_ed"),
    ("EDEBIYAT", "literature"), ("İNG. EDB. I", "literature"),
    ("DILBILIMI 1", "linguistics"), ("DİLBİL.", "linguistics"), ("DİL EDİN.", "linguistics"),
    ("Sosyolinguistik", "linguistics"),
    ("SESL. I", "language_skills"), ("SOZLU ILETISIM", "language_skills"),
    ("SÖZL. İLET.", "language_skills"), ("ANLATIM BEC.", "language_skills"),
    ("DIL BILGISI", "language_skills"), ("Gramer", "language_skills"), ("İNG. YAPISI", "language_skills"),
    ("OGRETIM ILKE VE YONTEMLERI", "pedagogy"), ("ÖĞR. TEKN.", "pedagogy"),
    ("TÜRK EĞT. TARİHİ", "pedagogy"), ("ÖLÇ. VE DEĞ.", "pedagogy"), ("DERS KİT. İNC.", "pedagogy"),
    ("ANAL. DÜŞ.", "pedagogy"), ("COCUK PSIKOLOJISI", "pedagogy"),
    ("BEDEN EĞT. VE SPOR", None), ("ÇEVRE EĞT.", None), ("Hızlı Okuma Teknikleri", None),
    ("Makine Öğrenmesi", None), ("Drama Çözümlemesi", None), ("Turist Rehberliği", None),
    ("Kitle İletişim Araçları", None), ("İfade Edebilme", None),
])
def test_elt_taxonomy_handles_documented_renderings(elt, title, domain):
    assert assign_domain(title, elt).domain == domain
