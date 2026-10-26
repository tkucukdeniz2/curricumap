# CurricuMap

Turn registrar transcripts into auditable student-by-domain competency matrices.

CurricuMap ingests a transcript export (CSV/XLSX) and assigns each course to a competency
domain defined in a declarative YAML taxonomy, using ordered keyword and regular-expression
rules, explicit overrides and an optional fuzzy fallback. It applies registrar cleaning
(retakes, sentinel grades, coverage) and aggregates grades into a student-by-domain matrix.
It then writes an audit (coverage, descriptives, Cronbach's alpha). Every course
assignment is traceable to the rule that produced it, and a course that matches nothing is
flagged rather than given a default domain.

## Installation

CurricuMap needs Python ≥ 3.10. Dependencies (pandas, numpy, pyyaml, jsonschema,
rapidfuzz, openpyxl, jinja2) are declared in `pyproject.toml` and installed automatically.
Install into a virtual environment, as below (on Windows: `py -m venv .venv`, then
`.venv\Scripts\activate`); many system Pythons refuse a bare `pip install`. From a clone of
the repository, which also registers the `curricumap` command:

```bash
git clone https://github.com/tkucukdeniz2/curricumap.git
cd curricumap
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

Or install a tagged release directly from GitHub into an active virtual environment:

```bash
pip install "curricumap @ git+https://github.com/tkucukdeniz2/curricumap@v0.2.0"
```

For development, an editable install with pytest and coverage, from the clone:

```bash
pip install -e ".[dev]"
pytest --cov=curricumap
```

`requirements.txt` pins the direct-dependency versions used for the paper's illustrative
example and benchmarks (Python 3.13.5); these pins need Python ≥ 3.12:
`pip install -r requirements.txt && pip install --no-deps .` The validation baselines are
pinned separately in `validation/requirements.txt`.

## Quickstart

Generate a synthetic transcript for a bundled taxonomy, then run the pipeline on it. These
are the commands of the paper's illustrative example:

```bash
curricumap synth --taxonomy elt_yok_2018 --out data --n-students 60 --seed 7
curricumap run --input data/transcript.csv --taxonomy elt_yok_2018 --out out
```

`run` writes five files to `out/`:

| File | Contents |
|---|---|
| `matrix_wide.csv` | One row per student, one column per domain (mean grade per domain). |
| `matrix_long.csv` | The same data in tidy long form: `student_id, domain, grade`. |
| `provenance.csv` | One row per course: assigned domain, method (`override`, `rule`, `fuzzy` or `unmatched`), the pattern and the text it matched, score, an ambiguity flag, and `n_titles`, the number of distinct titles printed under the course code. |
| `audit.json` | `taxonomy` (its id); `coverage`: `n_unmapped`, `unmapped_courses`, `n_ambiguous`, `n_title_conflicts`, `title_conflicts` (course codes printed with several titles) and `domain_sizes` (courses per domain); `prepare`, what cleaning dropped: `sentinel` grades, `no_grade` (records whose grade is blank or not a number, e.g. an absence code; also reported on stderr), `retakes` (records merged into another of the same student and course) and `low_coverage` (students left out of the matrix: below `coverage.min_domains`, or with no usable grade in any domain); `cronbach_missing`, how alpha treats missing grades; and `domains`, per domain: `alpha`, `k` (the courses with grades, alpha's items), `n_courses`, `n_students` (students with the domain), `n_alpha` (students alpha rests on; for `pairwise`, the fewest that share two courses), `mean`, `sd`, `skew`, `missing_pct` (matrix students without the domain), `item_missing_pct` (missing grades among all matrix students × all the domain's courses) and `n_complete` (students with every course grade of the domain). Values that cannot be computed are `null`. |
| `audit.html` | A self-contained, human-readable rendering of `audit.json`. |

A bundled taxonomy can be named instead of given as a path, so after `pip install .` these
commands work from any directory: `elt_yok_2018`, `math_ed_yok`, `engineering_mudek`,
`canmeds`, `bologna`. `curricumap --help` lists them.

## Input data

**Transcript export.** One row per student per course:

| column | required | meaning |
|---|:--:|---|
| `student_id` | ✅ | student key |
| `course_name` | ✅ | course title as printed by the registrar (any language); a row without one is an error |
| `grade` | ✅ | numeric grade |
| `course_id` | — | must identify one course; defaults to `course_name` |
| `date` | — | orders retakes when `dedup.keep: last`; ISO 8601 (`2020-06-23`) unless `io.date_format` gives the format |

Registrar systems name columns arbitrarily; map them in the run-config with `io.columns`
(e.g. `{ student_id: FKOgrenciID, grade: YuzlukNot }`); a mapped column that the export does
not have is an error; quote column names that YAML would read as numbers or booleans (`"2021"`,
`"No"`). CSV (UTF-8, with or without a byte order mark; comma-separated, or semicolon-separated
with decimal commas as Excel saves it in a Turkish locale) and `.xlsx` are read; save legacy `.xls` files as `.xlsx` first. Dates written as text are
read as ISO 8601 unless `io.date_format` gives their format, quoted, e.g. `io: { date_format: "%d.%m.%Y" }`
for `23.06.2020`; with `dedup.keep: last`, a date that does not match, or a retake without a date, is an
error rather than a guess (without a `date` column, `last` follows file order).

If your registrar reuses a code for different courses, map `course_id` to the title column
(`io.columns: { course_id: <title column> }`) or, if the export has no column named
`course_id`, leave it unmapped so that the title is used. Courses are then told apart by the
title as printed, so titles that differ only in case or spacing count as different courses.
`run` warns about a code printed with several titles, classifies it by its first title and
lists it under `coverage.title_conflicts` in `audit.json`. Rows without a `student_id` or
`course_id` are rejected with an error rather than dropped.

**Taxonomy (YAML).** The domains and the rules that assign courses to them. Rules are
evaluated in order and the first match wins; `any` lists substring keywords and `regex`
lists regular expressions, both matched against the title after case folding, which follows
Turkish rules (İ→i, I→ı) when `locale.language` is Turkish (`tr`, `tr-TR` or `tur`):

```yaml
taxonomy:
  id: my_programme
  label: "My programme"
  locale: { language: tr }
  domains:
    - { id: literature, label: "Literature" }
    - { id: pedagogy, label: "Pedagogy" }
  rules:
    - domain: literature            # subject before method: "Dil ve Edebiyat Öğretimi"
      any: ["edebiyat"]
    - domain: pedagogy
      any: ["öğretim", "öğretmenlik"]
      regex: ['\bs[ıi]n[ıi]f\b']     # Sınıf Yönetimi, never "sınıflandırma"
  overrides:
    - { course: "Özel Ders", domain: pedagogy }
```

`curricumap validate-taxonomy <file-or-name>` checks the file against the JSON Schema
and verifies that every rule refers to a defined domain and every regex compiles.
Unknown keys are rejected, so a misspelled key fails validation instead of being ignored;
the v0.1 keys `casefold`, `strategy` and `unmatched` are still accepted with the values
`locale-aware`, `ordered_rules` and `flag`, and have no effect.
Adopting CurricuMap for a new curriculum means writing such a file, not code. The bundled
`elt_yok_2018` taxonomy was written from the official national programme course lists of
the Turkish Council of Higher Education; since 2020 universities may adapt those
programmes, so add your local courses as rules or overrides. The other four bundled
taxonomies are compact illustrations and have not been validated on real data.

**Run-config (YAML, optional).** The cleaning and audit policy, as in `examples/sample_config.yaml`:

```yaml
prepare:
  dedup: { "on": [student_id, course_id], keep: max } # retakes: max | last (by date) | mean
  sentinel_grades: { values: [0], action: drop }      # e.g. 0 = did not attend
  coverage: { min_domains: 3 }                        # keep students covering >= 3 domains
  aggregate: { method: mean }                         # mean | median
audit:
  cronbach: { missing: column_mean }                  # missing grades: column_mean | listwise | pairwise
```

`student_id` and `course_id` always identify a record; `"on"` can add `course_name` or `date`
(`[student_id, course_id, date]` keeps attempts on different dates apart). Quote `"on"`:
YAML reads a bare `on` as `true`. Unknown keys and values of the wrong type are rejected.

A course of a domain that a student did not take is a missing grade for Cronbach's alpha.
`column_mean` (the default) replaces it by the course mean, which lowers alpha as the share
of missing grades grows; `listwise` uses only the students with every course grade of the
domain, and `pairwise` estimates each covariance from the students who have both grades (no
alpha when two courses share fewer than two students). `audit.json` reports each domain's
share of missing grades, its number of complete cases and the number of students alpha
rests on; `audit.html` shows alpha in grey, without a grade, when that number is below 30.

A small, deliberately messy sample transcript is in `examples/`; see
[`examples/README.md`](examples/README.md).

## Python API

```python
from curricumap import load_taxonomy, load_transcript, classify_courses, prepare, audit, write_reports

tax = load_taxonomy("elt_yok_2018")              # bundled name or path to a YAML file
transcript = load_transcript("export.xlsx", columns={"student_id": "FKOgrenciID"})
provenance = classify_courses(transcript[["course_id", "course_name"]], tax)
result = prepare(transcript, provenance, config={})
report = audit(transcript, provenance, result.wide, tax, config={}, dropped=result.dropped)
write_reports(report, "out")                     # audit.json and audit.html
```

## Validation and benchmarks

- [`validation/`](validation/README.md) tests the bundled ELT taxonomy on 143 real
  registrar course titles that the agents writing the taxonomy never opened (two of them did
  appear in their instructions or probes; see `validation/authoring/README.md`). It compares the taxonomy
  with string-similarity, supervised, embedding and LLM classifiers, and releases all
  data, prompts and predictions.
- [`benchmarks/`](benchmarks/benchmark.py) measures run time and peak memory from 60 to
  100,000 students.

## Maintainers

[`docs/architecture.md`](docs/architecture.md) is a one-page map of the six modules, the
data flow and where to change what. `CHANGELOG.md` lists changes per release.

## Citing

Please cite the software via [`CITATION.cff`](CITATION.cff) (Zenodo concept DOI
[10.5281/zenodo.22140689](https://doi.org/10.5281/zenodo.22140689), which always resolves to
the latest version).

## License

MIT
