from curricumap.classify import classify_courses
from curricumap.synth import generate

TR = """
taxonomy:
  id: tr
  label: TR
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: lang, label: Lang}]
  rules: [{domain: lang, any: ["İngilizce"]}]
"""


def test_generate_is_reproducible(make_tax):
    tax = make_tax()
    t1, c1 = generate(tax, n_students=20, seed=42)
    t2, c2 = generate(tax, n_students=20, seed=42)
    assert t1.equals(t2) and c1.equals(c2)


def test_generate_has_required_columns_and_every_student(make_tax):
    t, catalog = generate(make_tax(), n_students=40, seed=9)
    assert {"student_id", "course_id", "course_name", "grade"} <= set(t.columns)
    assert t["student_id"].nunique() == 40
    assert len(catalog) == 6                               # 2 domains x 3 courses


def test_courses_per_domain_controls_catalog_size(make_tax):
    _, catalog = generate(make_tax(), n_students=5, seed=1, courses_per_domain=10)
    assert len(catalog) == 20


def test_generated_courses_classify_under_turkish_locale(make_tax):
    tax = make_tax(TR)
    _, catalog = generate(tax, n_students=5, seed=3)
    assert classify_courses(catalog, tax)["domain"].notna().all()
