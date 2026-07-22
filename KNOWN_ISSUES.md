# Known issues / v0.1.x follow-ups

These were identified in the final whole-branch review and deliberately deferred
from the initial v0.1.0 build (none are correctness bugs in the core pipeline).

- **`.xls` ingestion.** `io.load_transcript` routes `.xls` to `pandas.read_excel`,
  which needs the `xlrd` package (not in the dependency allowlist; `openpyxl`
  only reads `.xlsx`). Either add `xlrd>=2` to dependencies or reject `.xls`
  with a clear message. `.xlsx` and CSV work today. Add a test.
- **`reconstruct_study_year` index alignment.** Uses `enroll_year.values`
  (positional). Safe as used (only called with aligned inputs) but a latent
  foot-gun if a caller passes `dates` and `enroll_year` with mismatched index
  order. Align on index, and guard `NaT` dates before `.astype(int)`.
- **CLI error UX.** Missing/unreadable spec/input files raise a traceback
  (exit code is correctly non-zero). Wrap to print `error: <msg>` and return 2.
- **Config validation.** `prepare()` raises `KeyError` on an unknown
  `dedup.keep` value. Validate the run-config or fall back with `.get(..., "max")`.
- **Docs.** State supported input formats as `.xlsx` and CSV until `.xls` is
  resolved.
