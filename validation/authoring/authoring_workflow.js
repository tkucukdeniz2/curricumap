// The workflow that drafted, critiqued and revised src/curricumap/taxonomies/elt_yok_2018.yaml
// (Claude Code workflow script, run on 2026-10-01). Paths are replaced by <repo> and
// <private-workspace>; the text is otherwise verbatim. Every tool call the five agents made is in
// tool_calls.jsonl; their structured reports are in ../results/taxonomy_authoring_record.json.

export const meta = {
  name: 'elt-taxonomy-blind-authoring',
  description: 'Author the revised ELT-YOK taxonomy from the official YOK programme lists only (blind to registrar data), then adversarially review and revise it',
  phases: [
    { title: 'Author', detail: 'write elt_yok_2018.yaml from yok_programmes.csv only' },
    { title: 'Review', detail: 'independent critiques: generality/overfitting, rule-order and substring hazards, leakage' },
    { title: 'Revise', detail: 'apply accepted critiques, re-verify 100% on the source list and the test suite' },
  ],
}

const REPO = '<repo>'
const PY = `${REPO}/.venv/bin/python`

const BLIND = `STRICT BLINDING PROTOCOL (this taxonomy will be evaluated on held-out registrar data, so any leakage invalidates the evaluation):
- You may read ONLY: ${REPO}/validation/data/yok_programmes.csv, the CurricuMap source code (${REPO}/src), its schema, tests, README/docs, and the other bundled taxonomies.
- You must NOT read, list, grep, or open anything under <private-workspace>, anything under /private/tmp or /tmp, any file named *catalog*, *iuc*, *registrar*, *transcript*.xlsx, or any git history/objects that could contain course lists from a real institution (do not run git log -p, git show, or git grep on old revisions).
- Do not search the web for any specific university's course catalogue. General knowledge of how Turkish registrar systems render course titles (UPPERCASE, Roman vs Arabic numerals, abbreviations such as "ÖĞR." for "ÖĞRETİMİ", missing diacritics) is allowed.`

const CONTEXT = `CurricuMap (repo ${REPO}) assigns course titles to competency domains with an ordered list of rules in a YAML taxonomy. Read src/curricumap/taxonomy.py and src/curricumap/classify.py first. Matching semantics: the course title is normalized with Turkish-aware casefolding (locale language "tr": İ->i, I->ı, then casefold) and whitespace collapsing; each rule has "any" (substring keywords, themselves normalized the same way) and/or "regex" (Python regular expressions applied with re.search to the NORMALIZED title, so write them in lowercase Turkish; they are not normalized); overrides (exact normalized-title match) take precedence over rules; rules are evaluated in order and the FIRST matching rule wins; a title matching several domains is flagged ambiguous; titles matching nothing are flagged "unmatched" (there is deliberately no catch-all default).

The source list ${REPO}/validation/data/yok_programmes.csv has 158 official course titles from the two national English Language Teaching (ELT) undergraduate programmes of the Turkish Council of Higher Education (YOK): the 2018 programme (compulsory courses plus its MB, GK and AE elective pools) and the 2006 programme (compulsory courses). Columns: programme, title, category (MB = teaching-profession knowledge, GK = general culture, AE/A = field courses), pool, domain (the label the taxonomy must reproduce), rule (why that label: R1 MB->pedagogy, R2 GK->general_ed, R3 field courses by subject matter, R4 second foreign language->general_ed).

The five domains, in this exact order (keep ids, labels and order): language_skills "Language Skills", pedagogy "Pedagogy", linguistics "Linguistics", literature "Literature", general_ed "General Education".`

const GOALS = `GOALS for src/curricumap/taxonomies/elt_yok_2018.yaml (replace the current file; keep id elt_yok_2018, label "ELT Teacher Education Curriculum (YÖK 2018)", locale tr/locale-aware, match.strategy ordered_rules, fuzzy disabled, defaults.unmatched flag):
1. Every one of the 158 source titles must be assigned exactly its labelled domain, with no title left unmatched (verify with a short Python check using curricumap.load_taxonomy + curricumap.classify.assign_domain over the CSV; also report how many source titles are flagged ambiguous).
2. Generalise: prefer few, meaningful rules that capture course FAMILIES via word stems (e.g. a stem that covers both "Dilbilim I" and "Dilbilimi 1") over enumerating full titles, so the taxonomy also works for registrar variants of these courses (uppercase, Roman/Arabic numerals, abbreviations, minor punctuation differences). Use overrides only where no reasonable general rule exists, and justify each override in a YAML comment.
3. Avoid over-broad substrings that would capture unrelated courses a real transcript contains (for example a bare "eğitim" would also match "Beden Eğitimi ve Spor" or "Müzik Eğitimi"; a bare "dil" matches almost everything). When a broad stem is needed, constrain it (word boundaries via regex, longer stems, or rule order) and explain the choice in a comment.
4. Order rules deliberately and explain the order in a header comment (e.g. why literature or linguistics precedes pedagogy for compound titles such as "Dil ve Edebiyat Öğretimi" or "Edimbilimi ve Dil Öğretimi").
5. The first rule of each domain must contain at least one plain keyword in "any", and synthetic course names formed as "<first keyword of that rule> 1/2/3" must classify into that domain (the test tests/test_taxonomy.py::test_every_bundled_taxonomy_classifies_its_synthetic_courses checks this).
6. Add a short header comment: authored from the official YOK 2018 and 2006 ELT programme course lists only, the domain convention (R1-R4), and the counts of rules/keywords/regexes/overrides.
7. Run the full test suite: cd ${REPO} && ${PY} -m pytest -q . Every test must pass. In particular tests/test_cli.py::test_paper_illustrative_example_reproduces_exactly and tests/test_cli.py::test_bundled_sample_transcript_runs_as_documented use this taxonomy. The sample transcript examples/sample_transcript.csv is a toy file with invented titles; if its expectations fail ONLY because the toy titles are not official YOK titles, do NOT bend the taxonomy to fit them; instead report exactly which toy titles fail and why (the orchestrator will update the toy file).
Do not modify any file other than src/curricumap/taxonomies/elt_yok_2018.yaml.`

const AUTHOR_SCHEMA = {
  type: 'object',
  properties: {
    yaml_written: { type: 'boolean' },
    n_rules: { type: 'number' }, n_keywords: { type: 'number' }, n_regex: { type: 'number' }, n_overrides: { type: 'number' },
    source_accuracy: { type: 'string', description: 'e.g. 158/158 correct, 0 unmatched, N ambiguous' },
    tests: { type: 'string', description: 'pytest summary line and any failing test names' },
    sample_transcript_issues: { type: 'array', items: { type: 'string' } },
    design_notes: { type: 'string' },
    files_read: { type: 'array', items: { type: 'string' }, description: 'every file path you read or listed, for the blinding audit' },
  },
  required: ['yaml_written', 'n_rules', 'n_keywords', 'n_regex', 'n_overrides', 'source_accuracy', 'tests', 'sample_transcript_issues', 'design_notes', 'files_read'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    issues: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      problem: { type: 'string' },
      example_titles: { type: 'array', items: { type: 'string' }, description: 'hypothetical or official titles that demonstrate the problem' },
      fix: { type: 'string' },
    }, required: ['severity', 'problem', 'example_titles', 'fix'] } },
    verdict: { type: 'string' },
  },
  required: ['issues', 'verdict'],
}

phase('Author')
const authored = await agent(`${BLIND}\n\n${CONTEXT}\n\n${GOALS}`, { label: 'author', phase: 'Author', schema: AUTHOR_SCHEMA })
if (!authored || !authored.yaml_written) {
  return { error: 'authoring failed', authored }
}
log(`Authored: ${authored.n_rules} rules, ${authored.n_keywords} keywords, ${authored.n_regex} regexes, ${authored.n_overrides} overrides; ${authored.source_accuracy}`)

phase('Review')
const LENSES = [
  { key: 'generality', prompt: 'Lens: GENERALISATION and OVERFITTING. Does each rule capture a course family via stems, or does it memorise full titles? Would the rules still classify plausible registrar variants of the SAME official courses (UPPERCASE Turkish with dotted/dotless I, "1/2" vs "I/II", abbreviations such as "ÖĞR." or "DİL BEC. ÖĞR.", punctuation like "Türkçe I: Yazılı Anlatım" vs "TÜRKÇE I YAZILI ANLATIM", missing diacritics such as "OGRETIM")? Construct concrete variant titles of official courses and actually run them through curricumap.classify.assign_domain to demonstrate failures.' },
  { key: 'hazards', prompt: 'Lens: FALSE POSITIVES, RULE ORDER, SUBSTRING HAZARDS. Construct plausible courses that a Turkish ELT transcript might contain but that are NOT in the official lists (university-wide electives such as "Beden Eğitimi ve Spor", "Müzik", "Afet Bilinci", "Girişimcilik", second foreign languages like "Almanca I", service courses, a German or French literature course, "Türk Dili ve Edebiyatı", "Bilgisayar Programlama") and run them through assign_domain. Report courses that would be silently assigned to a WRONG domain (a wrong assignment is worse than "unmatched", which is surfaced in the audit). Check the rule order for compound titles.' },
  { key: 'convention', prompt: 'Lens: CONVENTION FIDELITY and DOCUMENTATION. Check every rule against the labelled convention in the CSV (R1 MB->pedagogy, R2 GK->general_ed, R3 field courses by subject matter, R4 second foreign language->general_ed). Re-run the 158-title check yourself. Are the header comments accurate (counts, ordering rationale, provenance statement)? Are overrides justified? Is the YAML idiomatic and readable for a curriculum researcher who is not a programmer?' },
]
const reviews = await parallel(LENSES.map(l => () => agent(`${BLIND}\n\n${CONTEXT}\n\nYou are an independent, skeptical reviewer of the taxonomy file ${REPO}/src/curricumap/taxonomies/elt_yok_2018.yaml that another author just wrote to these goals:\n${GOALS}\n\n${l.prompt}\nDo NOT edit any file; only report issues with concrete evidence (titles you ran and the result).`, { label: `review:${l.key}`, phase: 'Review', schema: REVIEW_SCHEMA })))
const issues = reviews.filter(Boolean).flatMap((r, i) => r.issues.map(x => ({ lens: LENSES[i].key, ...x })))
log(`${issues.length} review issues (${issues.filter(i => i.severity === 'high').length} high)`)

phase('Revise')
const revised = await agent(`${BLIND}\n\n${CONTEXT}\n\n${GOALS}\n\nYou are revising ${REPO}/src/curricumap/taxonomies/elt_yok_2018.yaml after independent review. Evaluate each issue on its merits: fix the valid ones (especially any that cause silent WRONG assignments of plausible non-curricular courses, or that break registrar variants of official courses), and decline invalid ones with a reason. Keep the taxonomy readable and as small as the goals allow. Re-verify 158/158 on the source list and rerun the full test suite.\n\nReview issues (JSON):\n${JSON.stringify(issues, null, 1)}`, { label: 'revise', phase: 'Revise', schema: {
  type: 'object',
  properties: {
    ...AUTHOR_SCHEMA.properties,
    issue_decisions: { type: 'array', items: { type: 'object', properties: { problem: { type: 'string' }, decision: { type: 'string', enum: ['fixed', 'declined'] }, reason: { type: 'string' } }, required: ['problem', 'decision', 'reason'] } },
  },
  required: [...AUTHOR_SCHEMA.required, 'issue_decisions'],
} })
return { authored, issues, revised }
