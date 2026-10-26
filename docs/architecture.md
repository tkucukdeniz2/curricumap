# Architecture (for maintainers)

CurricuMap is about 770 lines of Python in six modules (plus `__init__`). Each pipeline stage is one
function, and each module holds one concept a user has to understand:

| Module | Concept | Public functions |
|---|---|---|
| `taxonomy.py` | The specification: Turkish-aware casefolding, JSON-Schema validation, loading, bundled taxonomies | `load_taxonomy`, `validate_taxonomy`, `bundled_taxonomies` |
| `classify.py` | Course-to-domain assignment with provenance | `assign_domain`, `classify_courses` |
| `prepare.py` | Ingest an export, validate the run-config, clean grades, aggregate to a matrix | `load_transcript`, `prepare` |
| `audit.py` | Coverage, descriptives, Cronbach's alpha; JSON/HTML report | `audit`, `cronbach_alpha`, `write_reports` |
| `synth.py` | Seeded synthetic transcripts | `generate` |
| `cli.py` | `validate-taxonomy`, `synth`, `run` | `main` |

Data files: `schemas/taxonomy.schema.json` (the spec contract), `taxonomies/*.yaml`
(bundled taxonomies, loadable by name), and `templates/audit.html.j2` (the report).

## Data flow of `curricumap run`

```
load_taxonomy(spec)                       -> Taxonomy
validate_config(config)                   -> settings with defaults filled in; error on an unknown key or a bad value
load_transcript(export, columns)          -> tidy DataFrame: student_id, course_id, course_name, grade[, date]
classify_courses(courses, taxonomy)       -> provenance: one row per course (domain, method, pattern, span, score, ambiguous, n_titles)
prepare(transcript, provenance, config)   -> wide and long student-by-domain matrices, and what cleaning dropped
    clean_grades(...)                     -> drops sentinel grades and records without a numeric grade, merges retakes (shared with audit)
audit(transcript, provenance, wide, ...)  -> dict: coverage, what cleaning dropped, per-domain descriptives, alpha, missing grades
write_reports(audit, out_dir)             -> audit.json, audit.html
```

## Design rules worth keeping

- **No silent defaults.** A course that matches no rule is flagged `unmatched` and listed
  in the audit; there is deliberately no catch-all domain, and empty keywords are rejected
  by the schema (an empty string would match every title). Unknown keys in a taxonomy or a
  run-config are rejected rather than ignored, and so is an `io.columns` mapping that names a
  column the export lacks; rows without a student id, course id or course title are rejected
  rather than dropped, and course codes printed with several titles are reported.
- **One cleaning path.** `prepare()` and `audit()` both call `clean_grades()`, so the
  reliability statistics describe exactly the grades that built the matrix.
- **Determinism.** Classification, cleaning and aggregation contain no randomness; `synth`
  is seeded. `tests/test_cli.py::test_paper_illustrative_example_reproduces_exactly` runs the
  paper's Listing 2 and pins the numbers of its illustrative example, and the validation
  tests in `tests/test_taxonomy.py` pin the ELT taxonomy's results on `validation/data/`.

## Where to change things

- New rule type or matching behaviour: `classify.py::_rule_hits`, the `rules` item in the schema, and
  `taxonomy.py` (`Rule`, `compiled_rules`, `load_taxonomy`, `validate_taxonomy`).
- New cleaning option: `prepare.py::clean_grades` / `prepare`, plus its key in `CONFIG_KEYS` and its
  default and check in `validate_config`, from which every stage reads its settings.
- New statistic in the report: `audit.py::audit` and `templates/audit.html.j2`.
- New bundled taxonomy: add `taxonomies/<name>.yaml`; the parametrised test in
  `tests/test_taxonomy.py` picks it up automatically.
- Editing a bundled taxonomy must keep the validation tests in `tests/test_taxonomy.py`
  green. An intended change of behaviour means re-running `validation/` and updating the
  frozen hash (`validation/results/frozen_taxonomy.sha256`) and the paper.

Tests mirror the modules one file each (`tests/test_<module>.py`). They share a two-domain
taxonomy and two fixtures (`spec_path`, `make_tax`) in `tests/conftest.py`; tests that need
another taxonomy define it inline. Run `pip install -e ".[dev]" && pytest --cov=curricumap`.
