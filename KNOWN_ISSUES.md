# Known issues

The v0.1.x follow-ups recorded after the initial release were resolved in 0.2.0 (see
`CHANGELOG.md`): `.xls` input now fails with a clear message, CLI errors are reported
without a traceback, and run-configs are validated.

Open:

- **"Türk Eğitim Tarihi"** is a teaching-profession course (pedagogy) in the 2018 programme
  and a general-culture course (general education) in the 2006 programme. A title-level rule
  cannot honour both, and the bundled `elt_yok_2018` taxonomy follows 2018. For a cohort on
  the 2006 programme, add an override to a copy of the taxonomy:

  ```yaml
  overrides:
    - { course: "Türk Eğitim Tarihi", domain: general_ed }
  ```
- **Course codes shared by different courses.** A course is identified by its `course_id`
  and classified by the first title printed under it. `run` warns when a code carries
  several titles and lists them under `coverage.title_conflicts` in `audit.json`; map
  `course_id` to the title column if your registrar reuses codes. Titles that differ only
  in case or spacing then count as different courses.
- **ASCII folding of Turkish letters** (ı→i, ş→s, ...) before matching could replace many of
  the ELT taxonomy's regular expressions with plain keywords. It would change the frozen,
  validated taxonomy, so it is left for a future version.
- **Legacy `.xls` exports** are not read; save them as `.xlsx` or CSV first. Supporting
  them would add the `xlrd` dependency for a format most registrar systems no longer emit.
- **Bundled taxonomies other than `elt_yok_2018`** (`math_ed_yok`, `engineering_mudek`,
  `canmeds`, `bologna`) are compact illustrations of the specification format for other
  disciplines. Unlike the ELT taxonomy, they have not been validated against a real
  registrar catalogue; adapt and validate them before use.
