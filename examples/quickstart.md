# Quickstart

This is a standalone copy of the two-command walkthrough from the top-level
`README.md`.

## Install

```bash
pip install -e .
```

## 1. Generate a synthetic transcript

```bash
curricumap synth \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --out /tmp/cm_demo \
  --n-students 40 \
  --seed 1
```

Output:

```
Wrote synthetic data to /tmp/cm_demo
```

This writes two files:

- `/tmp/cm_demo/transcript.csv` — columns `student_id, course_id,
  course_name, grade`, one row per (student, course) enrollment.
- `/tmp/cm_demo/catalog.csv` — the synthetic course catalog used to
  generate the transcript.

## 2. Run the classification/audit pipeline

```bash
curricumap run \
  --input /tmp/cm_demo/transcript.csv \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --out /tmp/cm_out
```

Output:

```
Wrote outputs to /tmp/cm_out
```

This writes five files to `/tmp/cm_out/`:

- **`matrix_wide.csv`** — one row per student, one column per competency
  domain, average grade per domain.
- **`matrix_long.csv`** — the same data in tidy long form:
  `student_id, domain, grade`.
- **`provenance.csv`** — one row per course, recording which domain it was
  assigned to, the method (`rule` or `fuzzy`), the matched
  pattern/keyword and span, the match score, and whether the assignment
  was ambiguous (matched more than one domain).
- **`audit.json`** — coverage statistics (unmapped/ambiguous course
  counts, domain sizes) and per-domain reliability/descriptives
  (Cronbach's alpha, number of items `k`, `n` students, mean, sd, skew,
  missing %).
- **`audit.html`** — a human-readable HTML rendering of `audit.json`.

## Optional: validate a taxonomy first

```bash
curricumap validate-taxonomy src/curricumap/examples/elt_yok_2018.yaml
```

```
Taxonomy is valid.
```

## Other bundled example taxonomies

`src/curricumap/examples/` also includes `bologna.yaml`, `canmeds.yaml`,
`engineering_mudek.yaml`, and `math_ed_yok.yaml` — swap `--taxonomy` in
either command above to try the pipeline against any of them.
