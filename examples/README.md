# Examples

## `sample_transcript.csv` — a small, realistic input

A five-student English Language Teaching (ELT) transcript that uses official course titles
of the 2018 national programme, ready to run against the bundled `elt_yok_2018` taxonomy.
It is deliberately *messy*, the way real registrar exports are, so it exercises retake
handling, sentinel grades, an unmapped course and a student with an empty domain:

| row(s) | what it demonstrates |
|---|---|
| student 1, `LS101` appears twice (86, then 55) | a **retaken** course: `dedup: keep max` keeps 86 |
| student 3, `PED202` grade `0` | a **non-attendance** sentinel: `sentinel_grades` drops it |
| `PE100` "Beden Eğitimi ve Spor" | an **off-curriculum** course: it matches no rule and is flagged `unmatched` |
| student 4 has no literature rows | **partial coverage**: the student still covers ≥ 3 domains and is kept |

The schema is the canonical one: `student_id, course_id, course_name, grade`
(`course_id` is optional; here it mirrors a registrar course code).

## Run it (from the repository root)

```bash
curricumap run \
  --input examples/sample_transcript.csv \
  --taxonomy elt_yok_2018 \
  --config examples/sample_config.yaml \
  --out out/
```

## What you get

- **`out/provenance.csv`**: every course-to-domain decision. The ten curricular courses
  map by rule; for example, `İngiliz Edebiyatı 1` goes to literature through the keyword
  `edebiyat`. `Beden Eğitimi ve Spor` is `unmatched`.
- **`out/matrix_wide.csv`**: the student-by-domain matrix (5 students × 5 domains).
  Student 1's Language Skills score is the mean of the retake's higher grade (86) and
  *Dinleme ve Sesletim 1* (84), i.e. 85. Student 3's Pedagogy score comes only from the
  attended course. Student 4's Literature cell is empty.
- **`out/audit.json`** / **`out/audit.html`**: coverage (1 unmapped course, 0 ambiguous),
  what cleaning dropped (`"prepare": {"sentinel": 1, "no_grade": 0, "retakes": 1, "low_coverage": 0}`), and
  per-domain Cronbach's alpha and descriptives. With five students the alphas are
  illustrative only, so the report shows them in grey, without a grade.

`sample_config.yaml` sets the cleaning policy: retake deduplication, sentinel drop,
minimum coverage of 3 domains, and mean aggregation; it also names the missing-grade
method of Cronbach's alpha. Without `--config`, no sentinel grades are dropped and no
coverage filter is applied.

## Generating your own

`curricumap synth --taxonomy <name-or-file> --out <dir>` writes a seeded synthetic
transcript for any taxonomy; see the top-level `README.md`.
