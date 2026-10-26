# How the bundled ELT taxonomy was written

`src/curricumap/taxonomies/elt_yok_2018.yaml` (v0.2.0) was drafted, critiqued and revised by five
instances of an LLM coding assistant (Claude Opus 5.5 in Claude Code) on 1 October 2026, before
the specification was frozen and applied to the held-out registrar catalogue.

| Step | Agent | Time (UTC) |
|---|---|---|
| Draft | `author` | 11:16–11:41 |
| Critique (in parallel) | `review:generality`, `review:hazards`, `review:convention` | 11:41–12:03 |
| Revision | `revise` | 12:03–12:41 |

Files:

- `authoring_workflow.js`: the workflow script that ran the five agents, with the instructions it
  gave them (the blinding protocol, the matching semantics, the goals and the three critique
  lenses). Local paths are replaced by `<repo>` and `<private-workspace>`.
- `tool_calls.jsonl`: the input of every tool call the five agents made (184 calls: file reads,
  shell commands, edits), in order, with the same path replacement. Tool outputs and the agents'
  own messages are not released. Replaying its Write and Edit calls reproduces the frozen
  taxonomy byte for byte (`../results/frozen_taxonomy.sha256`). Abridged structured reports of the
  agents are in `../results/taxonomy_authoring_record.json`.

What the record shows, and what it does not:

- **The agents did not open the catalogue.** They read only the repository's code, tests,
  documentation, examples, bundled taxonomies and `data/yok_programmes.csv`; the catalogue had
  been moved out of the repository. No registrar course code and none of the five titles outside
  both national programmes appears in the instructions or the tool calls.
- **Two registrar variants do appear.** The generalisation critique's instructions use
  *TÜRKÇE I YAZILI ANLATIM* as an example of dropped punctuation (`authoring_workflow.js`, in the
  `generality` lens), and the reviser's probe lists include *YABANCI DİL 1 (ALMANCA)*
  (`tool_calls.jsonl`, revise agent, 12:28–12:38 UTC). Both are among the ten catalogue titles in
  the variant stratum.
- **The instructions were not written blind.** They were written by the first author's AI
  assistant, which had already seen the catalogue. Besides the verbatim title above, the
  false-positive critique (`hazards` lens) was given eight hypothetical off-programme courses to
  try; two of them, *Afet Bilinci* (disaster awareness) and *Almanca I* (German), resemble catalogue
  titles (*AFET KÜLTÜRÜ*; *YABANCI DİL 1 (ALMANCA)*). The instructions also use the catalogue's
  abbreviation style (for example *DİL BEC. ÖĞR.*). Neither the variant titles nor the five titles
  outside both programmes are therefore a fully blind test, and the paper says so.
- **The draft was written without these titles.** The drafting agent saw none of them; of the
  above, its instructions share only the general abbreviation example *ÖĞR.*. Its draft, rebuilt by replaying its own Write and Edit calls, already assigned all 128
  exact and all 10 variant titles correctly, and 3 of the 5 titles outside both programmes (it sent
  the two international-student versions of the Atatürk course to pedagogy); the revision fixed
  those two.
- **Context from the private workspace reached the agents.** Claude Code adds, unrequested, the
  first author's memory index and a git-status file listing of the private working directory to
  the context of every agent it starts; the drafting agent reported this. Neither contains a
  course title, and the tool-call log shows that no agent opened a file outside the repository.
- **No human edited the rules.** The authors' input to the specification is the labelling
  convention and the labelled official list (`../data/yok_programmes.csv`), drafted with the help of
  the same AI assistant. The rules were written and revised by the agents and should be reviewed by
  a curriculum expert before reuse; the provenance table makes that review course by course.
