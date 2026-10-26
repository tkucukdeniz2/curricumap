# CurricuMap — SoftwareX manuscript

- **`main_softwarex.tex`**: the manuscript in the official Elsevier `elsarticle` SoftwareX
  template, revision 1 (CurricuMap v0.2.0). Compile with
  `pdflatex → bibtex → pdflatex → pdflatex`.
- **`generated/`**: LaTeX macros and tables. `validation/paper_numbers.py` writes the
  validation numbers and copies the effort and validation tables and the benchmark table and
  numbers (written by `benchmarks/benchmark.py`);
  `paper/software_numbers.py` writes `software_numbers.tex` (test count, coverage, and the
  counts, alphas and share of missing grades of the illustrative example) and the test count
  and coverage in row C5 of `docs/code-metadata.md`. Every table, and
  every number in the text that the software, the validation scripts or the benchmark
  produce, comes from these files; the remaining numbers describe the data, the study design
  or the hardware. Regenerate with
  `cd validation && python evaluate.py && python effort.py && python paper_numbers.py`, then,
  from the repository root, `python paper/software_numbers.py`.
- **`figures/`**: Figure 2 is a capture of the `audit.html` from the illustrative run.
  The data-flow diagram (Figure 1) is TikZ inside the manuscript.
- The source of the original submission is preserved in the git history (commit 72abb23, the
  last commit before revision 1).

Submission material (cover letter, response to reviewers, highlights) lives in
`submission/`, which is git-ignored.
