# Examples

## `sample_transcript.csv` — a realistic sample input

A small English Language Teaching (ELT) transcript, ready to run against the
bundled `elt_yok_2018.yaml` taxonomy. It is deliberately *messy*, the way real
registrar exports are, so it exercises every cleaning step:

| row(s) | what it demonstrates |
|---|---|
| student 1, `LS101` appears twice (55, then 81) | a **retaken** course — `dedup: keep max` keeps 81 |
| student 3, `PED202` grade `0` | a **non-attendance** sentinel — `sentinel_grades: drop` removes it |
| `PE100` "Beden Eğitimi ve Spor" | an **off-curriculum** course — matches no rule, flagged `unmatched` |
| student 4 has no literature rows | partial coverage — the student still covers ≥ 3 domains and is kept |

The schema is the canonical one: `student_id, course_id, course_name, grade`
(`course_id` is optional and here mirrors a real course code).

## Run it

```bash
curricumap run \
  --input examples/sample_transcript.csv \
  --taxonomy src/curricumap/examples/elt_yok_2018.yaml \
  --config examples/sample_config.yaml \
  --out out/
```

## What you get

- **`out/provenance.csv`** — every course → domain decision. The ten curricular
  courses map by keyword rule (e.g. `İngiliz Edebiyatı I → literature` via
  `edebiyat`); `Beden Eğitimi ve Spor` is `unmatched`.
- **`out/matrix_wide.csv`** — the `student × domain` matrix (5 students × 5
  domains). Student 1's language-skills score uses the retake's higher grade;
  student 3's pedagogy score comes only from the attended course; student 4's
  literature cell is empty.
- **`out/audit.json`** / **`out/audit.html`** — coverage (1 unmapped course, 0
  ambiguous) and per-domain Cronbach's alpha and descriptives.

`sample_config.yaml` sets the cleaning policy (retake dedup, sentinel drop,
minimum coverage of 3 domains, mean aggregation). Remove `--config` to run with
defaults (no sentinel drop, no coverage filter).

## Generating your own

`curricumap synth --taxonomy <spec> --out <dir>` writes a synthetic transcript
for any taxonomy — see the top-level `README.md` and `quickstart.md`.
