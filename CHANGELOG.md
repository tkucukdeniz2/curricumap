# Changelog

## 0.2.0 (2026-10)

Revision prompted by peer review of the SoftwareX submission.

### Changed
- **Consolidated the package from nine modules to six (plus `__init__`).** `text` was merged
  into `taxonomy`, `io` into `prepare`, and `report` into `audit`. The package-level API
  (`from curricumap import ...`) is unchanged apart from the new `bundled_taxonomies` and the
  removals listed below. Code importing the removed submodules (`curricumap.text`,
  `curricumap.io`, `curricumap.report`) must import from the package instead.
- **Rebuilt the bundled ELT taxonomy (`elt_yok_2018`)** from the official YÖK 2018 and 2006
  English Language Teaching programme course lists, including the 2018 elective pools.
  Its classification of a real registrar catalogue is reported in `validation/`.
- Bundled taxonomies moved from `src/curricumap/examples/` to `src/curricumap/taxonomies/`
  and can be referred to by name (`--taxonomy elt_yok_2018`) from any directory.
- The taxonomy schema rejects unknown keys at every level, so a misspelled key (`overides`,
  `regexes`, `lang`, `fuzy`, `defualts`) fails validation instead of being ignored. The v0.1
  keys `casefold`, `strategy` and `unmatched` are still accepted with the values
  `locale-aware`, `ordered_rules` and `flag`, and have no effect (v0.1 accepted any
  `casefold` or `unmatched` string).
- The run-config rejects unknown keys (including unknown field names under `io.columns`),
  keys that are not strings (YAML reads an unquoted `on:` as `true`;
  `examples/sample_config.yaml` and the README now write `"on":`), values of the wrong type
  (`sentinel_grades.values`, `dedup.on`, `io.columns`, `coverage.min_domains`), and an
  unknown `audit.cronbach.missing`.
- `student_id` and `course_id` always identify a record; `dedup.on` can add `course_name` or
  `date`, and a record whose added field is empty is kept instead of dropped.
- Transcript rows without a `student_id`, `course_id` or `course_name` are rejected with an
  error; the grouping used to drop them without notice (and pandas 2 read a blank title as a
  course named "nan").
- Cronbach's alpha is now computed only for the students in the delivered matrix, so the
  coverage filter applies to the reliability statistics too.
- In `audit.html`, alpha is shown in grey without a grade, and marked ‡, when it rests on
  fewer than 30 students (`n_alpha`: the domain's students, or with `listwise` the complete
  cases and with `pairwise` the fewest students sharing two courses): with so few students
  even unrelated grades can give α ≥ .70. The domain-level "missing %" column is replaced
  by "missing grades %" (`item_missing_pct`), and the note states how missing grades were
  handled.
- The summary line of `curricumap run` also reports the number of courses.
- `sentinel_grades.values` alone now drops the listed grades; `action`, if given, must be
  `drop` (previously a config without `action: drop` was silently ignored).
- With `dedup.keep: last`, retakes are ordered by the `date` column when present. Text dates are
  read as ISO 8601 unless `io.date_format` gives their format (e.g. `"%d.%m.%Y"`), and a date that
  does not match is an error rather than a guess.
- The paper's illustrative example, the README and `examples/quickstart.md` run without
  `--config`, so the commands work from any directory after `pip install .`.
- The README and the quickstart install into a virtual environment.

### Added
- Regular-expression rules (`regex:`), matched against the normalised title. The provenance
  `span` now holds the text that actually matched.
- `curricumap --version`, `--courses-per-domain` for `synth`, and `bundled_taxonomies()`.
- Run-config validation with clear messages; CLI errors print `error: ...` and exit with code 2.
- Semicolon-separated CSV with decimal commas, as Excel writes it in a Turkish locale, is read.
- Missing-grade handling for Cronbach's alpha (`audit.cronbach.missing`): `column_mean`
  (default, unchanged results), `listwise` and `pairwise`. `audit.json` reports the method
  (`cronbach_missing`) and, per domain, the share of missing course grades among all matrix
  students and all the domain's courses (`item_missing_pct`), the students with every course
  grade (`n_complete`) and the students alpha rests on (`n_alpha`).
- What cleaning dropped (sentinel grades, retake records merged by deduplication,
  low-coverage students): `PrepareResult.dropped`, the `prepare` key of `audit.json`
  (`audit(..., dropped=...)`), the CLI summary line and a line in `audit.html`.
- Course codes printed with several titles: the provenance column `n_titles`,
  `coverage.title_conflicts` and `coverage.n_title_conflicts` in `audit.json`, a warning on
  stderr and a warning line in `audit.html`.
- Tests that pin the ELT taxonomy's validated results (`validation/data/`) and the registrar
  renderings documented in its comments; the illustrative-example test runs the paper's
  Listing 2 verbatim; Reviewer 1's five-student noise scenario runs end to end.
- CI on macOS (Python 3.13) and a job that installs the built wheel with the pinned
  dependencies and runs the paper's commands outside the source tree.
- Validation study (`validation/`), scalability benchmark (`benchmarks/`), `docs/architecture.md`,
  `CITATION.cff`, `requirements.txt`, and test coverage in CI.

### Fixed
- With `dedup.keep: last`, a retake without a date is an error instead of silently counting as
  the latest attempt (attempts that `dedup.on` keeps apart need no date); without a `date`
  column, `last` follows file order (documented).
- A column mapped in `io.columns` that the export does not have was silently ignored, so a
  mistyped `date` mapping made `dedup.keep: last` follow file order; it is now an error that
  names the column.
- A cell holding only spaces counts as empty for `student_id`, `course_id` and
  `course_name`, and the row number in these errors counts blank lines, as a spreadsheet
  shows them.
- A file named `.xlsx` that is not an Excel workbook (a renamed `.xls`, an HTML export, a zip
  archive) gives a clear error instead of a traceback, and so does a CSV that is not UTF-8.
- `sentinel_grades.values` rejects booleans and non-finite numbers; `.nan` used to be accepted
  and made the retake count negative.
- Turkish case folding applies to any Turkish language tag (`tr`, `TR`, `tr-TR`, `tur`), not
  only to `tr`.
- `audit.html` prints means and SDs with two decimals and skew and alpha with three, shows
  the number of students behind alpha when it differs from the domain's n, and, like the CLI
  summary line, uses the singular for a count of one.
- `synth` rejects `--n-students` and `--courses-per-domain` below 1, which used to end in an
  unclear error or an empty file.
- With `dedup.keep: last`, text dates are stripped, and a date cell holding only spaces counts
  as empty instead of stopping the run.
- A numeric header cell in an `.xlsx` export (e.g. `2021`) can be mapped in `io.columns` by its
  text (`"2021"`); v0.1 accepted the unquoted number.
- `audit.json` gave `missing_pct` 0.0 for a domain that no matrix student has; it is now 100.0.
- `~` in an input path is expanded in every code path.
- `low_coverage` also counts students with no usable grade in any domain, who used to leave the
  matrix without being counted.
- Records whose grade is blank or not a number (for example an absence code) were silently ignored;
  they are now counted (`prepare.no_grade` in `audit.json`), counted in `audit.html` and reported on
  stderr.
- The audit report drew a full-width bar for a negative Cronbach's alpha. Negative values
  now show an empty bar and an explanatory note.
- `audit.json` is strict JSON: a mean, SD or skew that cannot be computed (no students,
  fewer than two for SD, fewer than three for skew) is `null` instead of `NaN`, and is shown
  as — in `audit.html`.
- An unknown `audit.cronbach.missing` (e.g. a typo) silently gave listwise deletion; it is
  now an error.
- `dedup.on` in `examples/sample_config.yaml` was read as the boolean key `true` and ignored.
- The report header showed "Cronbach α" upper-cased, so α looked like a Latin A; α, k and n
  now keep their case.
- Legacy `.xls` files fail with a clear message instead of a missing-dependency error;
  CSV files with a byte-order mark load correctly.
- Title matching normalises Unicode to composed form (NFC). For Turkish it also drops the combining
  dot left by text that was lower-cased without Turkish rules (`di̇lbi̇li̇mi̇` → `dilbilimi`).
- The schema rejects empty keywords, unknown fuzzy scorers and catch-all `unmatched` defaults.
- `curricumap validate-taxonomy` (and `run`) crashed with a traceback on a structurally
  malformed taxonomy, such as a rule written as a string or `domains` written as a mapping;
  they now report the schema errors.
- Run-config values of the wrong type (e.g. `sentinel_grades: { values: 0 }`, or
  `io.columns` written as a list) ended in a Python traceback; they are now reported as
  `error: ...`.
- `benchmarks/benchmark.py` printed the largest run time rounded twice (`\benchMaxTime` 2.1
  for a table value of 2.15); it now prints the table's two-decimal value.

### Removed
- `reconstruct_study_year`: nothing in the pipeline called it, and it needed an enrolment
  year that no input provides. `date` now serves deduplication only: it orders retakes
  under `dedup.keep: last` and can be a `dedup.on` field.
- `term` and `credits` as canonical transcript fields. Only a v0.1 `dedup.on` could use
  `term`; map such a column to `date` instead.
- The `casefold` and `unmatched` fields of `Taxonomy`, which had no effect, and its unused
  `domain_ids` property.
- `paper/main.tex`, a stale preview of the original submission, and
  `paper/figures/fig1_audit_report.png`, the original submission's figure, now replaced by
  `fig2_audit_report.png`; the submitted source is preserved in the git history (commit 72abb23).

## 0.1.0 (2026-08-28)

Initial release. The repository was made public on 2026-07-23.
