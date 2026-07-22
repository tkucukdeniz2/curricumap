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
