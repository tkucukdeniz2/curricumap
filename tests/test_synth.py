# tests/test_synth.py
from curricumap.taxonomy import load_taxonomy
from curricumap.synth import generate

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

def test_generate_is_reproducible(tmp_path):
    tax = _tax(tmp_path)
    t1, c1 = generate(tax, n_students=20, seed=42)
    t2, c2 = generate(tax, n_students=20, seed=42)
    assert t1.equals(t2)

def test_generate_has_required_columns_and_students(tmp_path):
    t, catalog = generate(_tax(tmp_path), n_students=15, seed=1)
    assert {"student_id", "course_id", "course_name", "grade"}.issubset(t.columns)
    assert t["student_id"].nunique() == 15
    assert len(catalog) >= 2

def test_generated_courses_classify_under_turkish_locale(tmp_path):
    from curricumap.classify import classify_courses
    p = tmp_path / "tr.yaml"
    p.write_text("""
taxonomy:
  id: tr
  label: TR
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: lang, label: Lang}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: ratio } }
  rules: [{domain: lang, any: ["ingilizce"]}]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    tax = load_taxonomy(p)
    _, catalog = generate(tax, n_students=5, seed=3)
    prov = classify_courses(catalog, tax)
    assert prov["domain"].notna().all()

def test_every_student_has_at_least_one_enrollment(tmp_path):
    t, _ = generate(_tax(tmp_path), n_students=40, seed=9)
    assert t["student_id"].nunique() == 40
