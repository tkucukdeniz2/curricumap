# CurricuMap — SoftwareX manuscript

Two LaTeX sources, same content, sharing `references.bib` and `figures/`:

- **`main_softwarex.tex`** — official Elsevier **elsarticle** SoftwareX template
  (submission format). Compile: `pdflatex → bibtex → pdflatex → pdflatex`.
  Single-column preprint (~11 pp); typesets to ~5 pp in the journal's final
  two-column format, within SoftwareX's 6-page limit.
- **`main.tex`** — portable `article`-class preview (compiles anywhere with one
  `pdflatex` run; inline bibliography). 6 pages.

Before submission: set the real GitHub URL (C2), attach Figure 1, and update the
two under-review citations (`can2025a`, `can2025b`) with final venues.
