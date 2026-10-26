"""LLM baselines: classify all held-out titles in one prompt, zero-shot or few-shot.

zero-shot: the domain definitions only (prompts/definitions.md)
few-shot:  the definitions plus the 158 labelled official programme titles, i.e. the same
           information the CurricuMap taxonomy was written from

Models:
  gemma   google Gemma 4 12B instruction-tuned (MLX 4-bit QAT conversion), run locally;
          run 0 is greedy (deterministic), runs 1..N sample with temperature 1.0,
          top-p 0.95, top-k 64 and seed = run number
  claude  Claude Opus 5.5 through the Claude Code CLI in print mode with all tools
          disabled, a fixed system prompt and default sampling; runs 1..N

Usage: python predict_llm.py {gemma,claude} {zeroshot,fewshot} RUNS
Raw responses are kept in results/llm_raw/ for audit.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time

from common import ABSTAIN, DOMAINS, RESULTS, definitions, source_courses, target_courses, write_predictions

GEMMA = ("mlx-community/gemma-4-12B-it-qat-4bit", "e70c6b3ba0979b3357dcd2f223ad8bde7787a6b6")
CLAUDE = "claude-opus-5-5"
SYSTEM = "You are an expert annotator of teacher-education curricula. Follow the output format exactly."


def build_prompt(mode: str, titles: list[str]) -> str:
    parts = [definitions()]
    if mode == "fewshot":
        ref = "\n".join(f"- {c['title']} -> {c['domain']}" for c in source_courses())
        parts.append("Official course titles of the national ELT programmes (2018 and 2006) with their "
                     f"domains, for reference:\n{ref}")
    listing = "\n".join(f"{i}. {t}" for i, t in enumerate(titles, 1))
    parts.append("Classify each numbered course title below. Answer with a single JSON object that maps "
                 "every number (as a string) to exactly one of: " + ", ".join(DOMAINS) +
                 ". Output only the JSON object.\n\n" + listing)
    return "\n\n".join(parts)


def parse(text: str, n: int) -> tuple[list[str], int]:
    m = re.search(r"\{.*\}", text, flags=re.S)
    obj = json.loads(m.group(0)) if m else {}
    labels, bad = [], 0
    for i in range(1, n + 1):
        lab = str(obj.get(str(i), "")).strip()
        if lab not in DOMAINS:
            bad += 1
            lab = ABSTAIN
        labels.append(lab)
    return labels, bad


def run_gemma(prompt: str, runs: int, out):
    import mlx.core as mx
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler
    model, tok = load(GEMMA[0], revision=GEMMA[1])
    chat = tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                                   add_generation_prompt=True, tokenize=False, enable_thinking=False)
    for run in range(0, runs + 1):
        if run == 0:
            sampler = make_sampler(temp=0.0)
        else:
            mx.random.seed(run)
            sampler = make_sampler(temp=1.0, top_p=0.95, top_k=64)
        t0 = time.perf_counter()
        text = generate(model, tok, prompt=chat, max_tokens=6000, sampler=sampler, verbose=False)
        out(run, text, time.perf_counter() - t0)


def run_claude(prompt: str, runs: int, out):
    with tempfile.TemporaryDirectory() as sandbox:   # empty working dir: no project context
        for run in range(1, runs + 1):
            t0 = time.perf_counter()
            res = subprocess.run(
                ["claude", "-p", "--model", CLAUDE, "--system-prompt", SYSTEM, "--tools", "",
                 "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
                 "--output-format", "json"],
                input=prompt, capture_output=True, text=True, cwd=sandbox, timeout=900)
            payload = json.loads(res.stdout)
            if payload.get("is_error"):
                raise RuntimeError(f"claude run {run} failed: {payload.get('result')}")
            out(run, payload["result"], time.perf_counter() - t0)


def main(model: str, mode: str, runs: int) -> None:
    titles = [c["title"] for c in target_courses()]
    prompt = build_prompt(mode, titles)
    raw_dir = RESULTS / "llm_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    system = f"{model}_{mode}"

    def out(run: int, text: str, secs: float) -> None:
        name, k = (f"{system}_greedy", 1) if run == 0 else (system, run)   # Gemma's greedy run
        (raw_dir / f"{name}__run{k}.txt").write_text(text, "utf-8")
        labels, bad = parse(text, len(titles))
        write_predictions(name, k, [{"title": t, "predicted": lab} for t, lab in zip(titles, labels)])
        print(f"{name} run {k}: {secs:.1f}s, {bad} missing/invalid labels", flush=True)

    (raw_dir / f"{system}__prompt.txt").write_text(f"[system]\n{SYSTEM}\n\n[user]\n{prompt}", "utf-8")
    {"gemma": run_gemma, "claude": run_claude}[model](prompt, runs, out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
