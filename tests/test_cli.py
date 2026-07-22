import json
from pathlib import Path
from curricumap.cli import main

EX = Path("src/curricumap/examples/elt_yok_2018.yaml")  # created in Task 13

def test_validate_taxonomy_ok(capsys, tmp_path):
    spec = tmp_path / "t.yaml"
    spec.write_text("""
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: d1, label: D1}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: ratio } }
  rules: [{domain: d1, any: ["okuma"]}]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    rc = main(["validate-taxonomy", str(spec)])
    assert rc == 0
    assert "valid" in capsys.readouterr().out.lower()

def test_synth_then_run_end_to_end(tmp_path):
    spec = tmp_path / "t.yaml"
    spec.write_text("""
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: language_skills, label: LS}, {id: pedagogy, label: Ped}]
  match: { strategy: ordered_rules, fuzzy: { enabled: false, threshold: 0.9, scorer: ratio } }
  rules: [{domain: language_skills, any: ["okuma"]}, {domain: pedagogy, any: ["öğretim"]}]
  defaults: { unmatched: flag }
""", encoding="utf-8")
    data_dir = tmp_path / "data"
    assert main(["synth", "--taxonomy", str(spec), "--out", str(data_dir),
                 "--n-students", "20", "--seed", "1"]) == 0
    out = tmp_path / "out"
    assert main(["run", "--input", str(data_dir / "transcript.csv"),
                 "--taxonomy", str(spec), "--out", str(out)]) == 0
    assert (out / "matrix_wide.csv").exists()
    assert (out / "audit.json").exists()
    audit = json.loads((out / "audit.json").read_text("utf-8"))
    assert "language_skills" in audit["domains"]
