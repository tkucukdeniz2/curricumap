# tests/test_taxonomy.py
import textwrap
from curricumap.taxonomy import load_taxonomy, validate_taxonomy

VALID = {
    "taxonomy": {
        "id": "t1", "label": "T1",
        "locale": {"language": "tr", "casefold": "locale-aware"},
        "domains": [{"id": "d1", "label": "D1"}, {"id": "d2", "label": "D2"}],
        "match": {"strategy": "ordered_rules",
                  "fuzzy": {"enabled": True, "threshold": 0.88, "scorer": "token_set_ratio"}},
        "rules": [{"domain": "d1", "any": ["okuma"]}, {"domain": "d2", "any": ["öğretim"]}],
        "overrides": [{"course": "X", "domain": "d1"}],
        "defaults": {"unmatched": "flag"},
    }
}

def test_validate_accepts_valid_spec():
    assert validate_taxonomy(VALID) == []

def test_validate_rejects_rule_referencing_unknown_domain():
    bad = {"taxonomy": {**VALID["taxonomy"],
           "rules": [{"domain": "nope", "any": ["x"]}]}}
    errors = validate_taxonomy(bad)
    assert any("nope" in e for e in errors)

def test_load_taxonomy_from_yaml(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text(textwrap.dedent("""
        taxonomy:
          id: t1
          label: T1
          locale: { language: tr, casefold: locale-aware }
          domains: [{id: d1, label: D1}]
          match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: token_set_ratio } }
          rules: [{domain: d1, any: ["okuma"]}]
          defaults: { unmatched: flag }
    """), encoding="utf-8")
    tax = load_taxonomy(p)
    assert tax.id == "t1"
    assert tax.language == "tr"
    assert tax.domains[0].id == "d1"
    assert tax.rules[0].patterns == ["okuma"]
    assert tax.fuzzy.enabled is False
    assert tax.unmatched == "flag"
