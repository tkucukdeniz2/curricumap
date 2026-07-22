# CurricuMap

Turn registrar transcripts into auditable competency-domain matrices.

CurricuMap ingests a course transcript (CSV/XLSX), classifies each course
into competency domains defined by a YAML taxonomy (via keyword/regex rules,
overrides, and optional fuzzy matching), aggregates student grades into a
domain-level matrix, and produces an audit (coverage, Cronbach's alpha,
descriptives) so every mapping decision is traceable back to the course that
produced it.

## Install

```bash
pip install -e .
```

Requires Python >= 3.10. Dependencies: pandas, numpy, pyyaml, jsonschema,
rapidfuzz, openpyxl, jinja2.

## Quickstart

CurricuMap ships with example taxonomies (ELT/YÖK 2018, Bologna, CanMEDS,
MÜDEK engineering, math education) under `src/curricumap/examples/`. The
fastest way to see the whole pipeline run is to generate a synthetic
transcript against one of them and then run the classification/audit
pipeline on it.

### 1. Generate a synthetic transcript

```bash
curricumap synth \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --out /tmp/cm_demo \
  --n-students 40 \
  --seed 1
```

This writes `/tmp/cm_demo/transcript.csv` (student_id, course_id,
course_name, grade) and `/tmp/cm_demo/catalog.csv` (the synthetic course
catalog), built so that every course name matches one of the taxonomy's
keyword rules.

### 2. Run the pipeline

```bash
curricumap run \
  --input /tmp/cm_demo/transcript.csv \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --out /tmp/cm_out
```

This classifies every course into a domain, aggregates grades per student
per domain, audits coverage and internal consistency, and writes five files
to `/tmp/cm_out/`:

| File | Contents |
|---|---|
| `matrix_wide.csv` | One row per student, one column per domain, average grade per domain. |
| `matrix_long.csv` | The same data in tidy long form: `student_id, domain, grade`. |
| `provenance.csv` | One row per course: which domain it was assigned to, by which method (`rule` or `fuzzy`), which pattern/keyword matched, the match score, and whether the assignment was ambiguous. |
| `audit.json` | Coverage stats (unmapped/ambiguous course counts, domain sizes) and per-domain reliability/descriptives (Cronbach's alpha, k items, n, mean, sd, skew, missing %). |
| `audit.html` | A human-readable HTML rendering of `audit.json`, ready to attach to a manuscript or share with a curriculum committee. |

## Other commands

Validate a taxonomy YAML file against the spec (checks required keys,
domain/rule structure, and reports unresolved schema errors):

```bash
curricumap validate-taxonomy src/curricumap/examples/elt_yok_2018.yaml
```

`curricumap run` also accepts an optional `--config path/to/config.yaml` for
overriding input column names and cleaning/aggregation policy (dedup rule,
sentinel-grade handling, minimum coverage, aggregation method).

## Python API

The same building blocks are importable directly:

```python
from curricumap import load_taxonomy, load_transcript, classify_courses, prepare, generate

tax = load_taxonomy("src/curricumap/examples/elt_yok_2018.yaml")
transcript = load_transcript("transcript.csv")
```

See `docs/code-metadata.md` for the SoftwareX code-metadata table and
`examples/quickstart.md` for a standalone copy of the walkthrough above.
