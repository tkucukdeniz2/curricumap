# tests/test_examples_golden.py
import pytest
from pathlib import Path
from curricumap.taxonomy import load_taxonomy
from curricumap.synth import generate
from curricumap.classify import classify_courses

EXAMPLES = sorted(Path("src/curricumap/examples").glob("*.yaml"))

@pytest.mark.parametrize("spec", EXAMPLES, ids=lambda p: p.stem)
def test_every_shipped_taxonomy_classifies_all_synthetic_courses(spec):
    tax = load_taxonomy(spec)
    transcript, catalog = generate(tax, n_students=30, seed=7)
    prov = classify_courses(catalog.rename(columns={}), tax)
    # synthetic courses are generated from rule patterns -> all must map
    assert prov["domain"].notna().all(), \
        f"unmapped in {spec.stem}: {prov[prov.domain.isna()].course_name.tolist()}"
    assert set(prov["domain"]) <= tax.domain_ids
