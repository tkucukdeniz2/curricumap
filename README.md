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

## Input data and data flow

CurricuMap takes three inputs and turns them into an audited matrix:

```
  transcript export (CSV/XLSX)  ─┐
  taxonomy spec (YAML)           ├─►  io ─► classify ─► prepare ─► audit ─► report
  run-config (YAML, optional)   ─┘                                            │
                                                                              ▼
              matrix_wide.csv · matrix_long.csv · provenance.csv · audit.json · audit.html
```

**1. Transcript export** — one row per student-per-course, in a tidy schema:

| column | required | meaning |
|---|:--:|---|
| `student_id` | ✅ | student key |
| `course_name` | ✅ | free-text course title (any language) |
| `grade` | ✅ | numeric grade |
| `course_id` | — | defaults to `course_name` |
| `term`, `date`, `credits` | — | `date` enables study-year reconstruction |

Registrar systems use arbitrary column names; map them onto this schema with
`io.columns` in the run-config (e.g. `{ student_id: FKOgrenciID, grade: YuzlukNot }`).

**2. Taxonomy spec (YAML)** — the competency domains and the keyword / override /
fuzzy rules that assign courses to them (see `src/curricumap/examples/`).
Adopting the tool for a new curriculum means writing this file, not code.

**3. Run-config (YAML, optional)** — the cleaning and aggregation policy: retake
deduplication, sentinel-grade handling, coverage filtering, aggregation method,
and the column mapping above.

### Try it on the bundled sample

A small, realistic sample transcript ships in `examples/`, so you can see the
whole flow without generating synthetic data:

```bash
curricumap run \
  --input examples/sample_transcript.csv \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --config examples/sample_config.yaml \
  --out out/
```

`examples/sample_transcript.csv` deliberately contains the mess real exports
carry: a **retaken** course (two rows for one student/course), a
**non-attendance** grade encoded as a sentinel `0`, and an **off-curriculum**
course (`Beden Eğitimi ve Spor`) that maps to no competency domain. The run
keeps the higher retake grade, drops the sentinel, flags the off-curriculum
course as unmapped in `provenance.csv`, and writes the 5×5 competency matrix.
See [`examples/README.md`](examples/README.md) for a full walkthrough.

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
