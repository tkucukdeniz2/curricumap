# Quickstart

A standalone copy of the walkthrough in the top-level `README.md`, identical to the
illustrative example in the paper.

## Install

```bash
git clone https://github.com/tkucukdeniz2/curricumap.git
cd curricumap
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

## 1. Generate a synthetic transcript

```bash
curricumap synth --taxonomy elt_yok_2018 --out data --n-students 60 --seed 7
```

This writes `data/transcript.csv` (878 grade records: `student_id, course_id,
course_name, grade`, including injected retakes and sentinel zeros) and `data/catalog.csv`
(the 15 synthetic courses). `elt_yok_2018` names a bundled taxonomy, so after
`pip install .` the commands work from any directory.

## 2. Run the pipeline

```bash
curricumap run --input data/transcript.csv --taxonomy elt_yok_2018 --out out
```

Output:

```
Wrote outputs to out: 60 students x 5 domains; 15 courses (0 unmapped, 0 ambiguous); dropped 0 sentinel grades, 64 retake records and 0 low-coverage students
```

Without a run-config no grade counts as a sentinel, so each injected zero is resolved with
the retakes (the highest grade is kept). With `--config examples/sample_config.yaml`, run
from the repository root, the line reports 24 sentinel grades and 40 retake records instead,
and the matrices are the same.

`out/` now holds `matrix_wide.csv`, `matrix_long.csv`, `provenance.csv`, `audit.json`
and `audit.html`. The per-domain Cronbach's alphas are .769 (Language Skills),
.767 (Pedagogy), .761 (Linguistics), .819 (Literature) and .781 (General Education).

## Optional: validate a taxonomy

Give a bundled taxonomy name or the path to your own YAML file:

```bash
curricumap validate-taxonomy elt_yok_2018
```

## Other bundled taxonomies

`math_ed_yok`, `engineering_mudek`, `canmeds` and `bologna` illustrate the specification
format for other disciplines; swap the `--taxonomy` value to try them.
