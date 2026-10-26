"""Score every prediction file against the reference labels and the official YOK categories.

Outputs (results/):
  metrics_runs.csv      one row per system and run
  metrics_summary.csv   one row per system (mean, min and max over runs; stability across runs)
  errors.csv            every misclassified title of each system's first scored run
  table_validation.tex  the LaTeX table used in the paper
"""
from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np
from sklearn.metrics import cohen_kappa_score, f1_score

from common import ABSTAIN, DOMAINS, PRED, RESULTS, read_csv, source_courses, target_courses
from curricumap.taxonomy import normalize

REFERENCE_SYSTEM = "curricumap_v0.2.0"  # paired tests compare every system with this one
STRATA = ("exact", "variant", "unseen")

# Official category -> domains compatible with it under the convention (R1-R3). A title
# without an official category ("none") counts as compatible with every domain.
COMPATIBLE = {"MB": {"pedagogy"}, "GK": {"general_ed"},
              "AE": {"language_skills", "linguistics", "literature", "pedagogy"},
              "A": {"language_skills", "linguistics", "literature", "pedagogy"},
              "none": set(DOMAINS)}

TABLE = [  # deterministic systems shown in the paper: (key, label, input); sampled runs are in the CSVs
    ("curricumap_v0.2.0", "CurricuMap rules (v0.2.0)", "L"),
    ("curricumap_lookup", "CurricuMap exact lookup", "L"),
    ("curricumap_adapted", "CurricuMap v0.2.0 + additions", "L"),
    ("curricumap_v0.1.0", "CurricuMap, v0.1.0 taxonomy", "--"),
    ("string_1nn", "String similarity", "L"),
    ("charngram_lr", "Character $n$-grams", "L"),
    ("e5_1nn", "E5, nearest title", "L"),
    ("e5_zeroshot", "E5, zero-shot", "D"),
    ("gemma_zeroshot_greedy", "Gemma 4 12B, zero-shot", "D"),
    ("gemma_fewshot_greedy", "Gemma 4 12B, few-shot", "L+D"),
    ("claude_zeroshot", "Claude Opus 5.5, zero-shot", "D"),
    ("claude_fewshot", "Claude Opus 5.5, few-shot", "L+D"),
]


def stratum(course: dict) -> str:
    """exact: the official title after CurricuMap's normalisation (case folding, whitespace);
    variant: another registrar rendering of an official title; unseen: in neither programme."""
    if not course["programme_title"]:
        return "unseen"
    same = normalize(course["title"], "tr") == normalize(course["programme_title"], "tr")
    return "exact" if same else "variant"


def stem(title: str) -> str:
    """The title without course numbers, so that numbered courses form one cluster."""
    t = re.sub(r"\b(ıv|ııı|ıı|ı|iv|iii|ii|i)\b", " ", normalize(title, "tr"))
    return re.sub(r"\s+", " ", re.sub(r"\d+", " ", t)).strip()


def loose_key(title: str) -> str:
    """The title after CurricuMap's normalisation, without diacritics, punctuation or spaces."""
    t = unicodedata.normalize("NFD", normalize(title, "tr"))
    return re.sub(r"[\W_]+", "", "".join(ch for ch in t if not unicodedata.combining(ch)))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar test: binomial test of the b + c discordant titles."""
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def fleiss_kappa(label_runs: list[list[str]]) -> float:
    """Fleiss' kappa with runs as raters and titles as subjects."""
    cats = DOMAINS + [ABSTAIN]
    n_raters = len(label_runs)
    counts = np.array([[sum(run[i] == c for run in label_runs) for c in cats]
                       for i in range(len(label_runs[0]))], dtype=float)
    p_i = ((counts * (counts - 1)).sum(axis=1)) / (n_raters * (n_raters - 1))
    p_bar = p_i.mean()
    p_j = counts.sum(axis=0) / counts.sum()
    p_e = (p_j ** 2).sum()
    return float((p_bar - p_e) / (1 - p_e)) if p_e < 1 else 1.0


def score(ref, pred, official, strata, base_ok) -> dict:
    n = len(ref)
    correct = [r == p for r, p in zip(ref, pred)]
    covered = [p != ABSTAIN for p in pred]
    k, n_cov = sum(correct), sum(covered)
    lo, hi = wilson(k, n)
    b = sum(x and not y for x, y in zip(base_ok, correct))  # reference system right, this one wrong
    c = sum(y and not x for x, y in zip(base_ok, correct))
    out = {
        "n": n,
        "coverage": n_cov / n,
        "accuracy": k / n, "acc_lo": lo, "acc_hi": hi,
        "acc_covered": (sum(c_ for c_, v in zip(correct, covered) if v) / n_cov) if n_cov else float("nan"),
        "macro_f1": f1_score(ref, pred, labels=DOMAINS, average="macro", zero_division=0),
        "kappa": cohen_kappa_score(ref, pred, labels=DOMAINS + [ABSTAIN]),
        "official_consistency": sum(p in COMPATIBLE[o] for p, o in zip(pred, official)) / n,
        "mcnemar_b": b, "mcnemar_c": c, "mcnemar_p": mcnemar_exact(b, c),
    }
    for s in STRATA:
        idx = [i for i, x in enumerate(strata) if x == s]
        out[f"n_{s}"] = len(idx)
        out[f"correct_{s}"] = sum(correct[i] for i in idx)
        out[f"assigned_{s}"] = sum(covered[i] for i in idx)
    return out


def main() -> None:
    target = target_courses()
    titles = [c["title"] for c in target]
    ref = [c["domain"] for c in target]
    official = [c["official_category"] for c in target]
    strata = [stratum(c) for c in target]
    curriculum = {c["title"]: c["curriculum"] for c in target}
    n_clusters = len({stem(t) for t in titles})
    loose = {loose_key(c["title"]): c["domain"] for c in source_courses()}
    n_variant_loose = sum(loose.get(loose_key(c["title"])) == c["domain"]
                          for c, s in zip(target, strata) if s == "variant")
    print(f"strata {Counter(strata)}; {n_clusters} title clusters")

    runs: dict[str, dict[int, list[str]]] = defaultdict(dict)
    for path in sorted(PRED.glob("*__run*.csv")):
        system, run = path.stem.rsplit("__run", 1)
        by_title = {r["title"]: r["predicted"] for r in read_csv(path)}
        runs[system][int(run)] = [by_title.get(t, ABSTAIN) for t in titles]
    base_ok = [r == p for r, p in zip(ref, next(iter(runs[REFERENCE_SYSTEM].values())))]

    RESULTS.mkdir(parents=True, exist_ok=True)
    run_rows, summary, error_rows = [], [], []
    ref_score = score(ref, ref, official, strata, base_ok)
    print(f"reference self-check: official-category consistency {ref_score['official_consistency']:.3f}")
    for system, by_run in runs.items():
        scored = {run: score(ref, labels, official, strata, base_ok)
                  for run, labels in sorted(by_run.items())}
        for run, s in scored.items():
            run_rows.append({"system": system, "run": run, **s})
        main_runs = list(scored)
        agg = {key: float(np.mean([scored[r][key] for r in main_runs]))
               for key in ("coverage", "accuracy", "acc_covered", "macro_f1", "kappa",
                           "official_consistency")}
        accs = [scored[r]["accuracy"] for r in main_runs]
        agg["accuracy_sd"] = float(np.std(accs, ddof=1)) if len(main_runs) > 1 else 0.0
        agg["accuracy_min"], agg["accuracy_max"] = min(accs), max(accs)
        label_runs = [by_run[r] for r in main_runs]
        agg["n_runs"] = len(main_runs)
        agg["identical_all_runs"] = float(np.mean([len({lr[i] for lr in label_runs}) == 1
                                                   for i in range(len(titles))]))
        agg["fleiss_kappa_runs"] = fleiss_kappa(label_runs) if len(label_runs) > 1 else 1.0
        first = scored[main_runs[0]]
        for key in ("acc_lo", "acc_hi", "mcnemar_b", "mcnemar_c", "mcnemar_p",
                    *[f"{p}_{s}" for s in STRATA for p in ("n", "correct", "assigned")]):
            agg[key] = first[key]
        agg["mcnemar_p_max"] = max(scored[r]["mcnemar_p"] for r in main_runs)
        agg["mcnemar_p_min"] = min(scored[r]["mcnemar_p"] for r in main_runs)
        for cur in ("2018", "2006", "other"):
            idx = [i for i, t in enumerate(titles) if curriculum[t] == cur]
            agg[f"acc_{cur}"] = float(np.mean([ref[i] == by_run[main_runs[0]][i] for i in idx])) \
                if idx else float("nan")
        summary.append({"system": system, **agg})
        lab = by_run[main_runs[0]]
        for i, t in enumerate(titles):
            if ref[i] != lab[i]:
                error_rows.append({"system": system, "title": t, "stratum": strata[i],
                                   "curriculum": curriculum[t], "official_category": official[i],
                                   "reference": ref[i], "predicted": lab[i]})

    def dump(name, rows):
        with open(RESULTS / name, "w", encoding="utf-8", newline="") as fh:
            keys = list(dict.fromkeys(k for r in rows for k in r))
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    dump("metrics_runs.csv", run_rows)
    dump("metrics_summary.csv", summary)
    dump("errors.csv", error_rows)

    by_sys = {s["system"]: s for s in summary}
    pc = lambda x: f"{100 * x:.1f}"  # noqa: E731

    def pval(s) -> str:
        if s["system"] == REFERENCE_SYSTEM:
            return "--"
        p = s["mcnemar_p"]
        return "$<$0.001" if p < 0.001 else f"{p:.3f}"

    n_by = {st: by_sys[REFERENCE_SYSTEM][f"n_{st}"] for st in STRATA}
    lines = [r"\begin{tabular}{@{}llrrcrrrr@{}}", r"\toprule",
             r" & & & & & \multicolumn{3}{c}{Correct titles} & \\ \cmidrule(lr){6-8}",
             r"System & Input & Cov. & Acc. & 95\% CI & Exact & Variant & Unseen & $p$ \\",
             f" & & (\\%) & (\\%) & (\\%) & ({n_by['exact']}) & ({n_by['variant']}) & ({n_by['unseen']}) & \\\\",
             r"\midrule"]
    for key, label, inp in TABLE:
        if key not in by_sys:
            continue
        s = by_sys[key]
        lines.append(f"{label} & {inp} & {pc(s['coverage'])} & {pc(s['accuracy'])} & "
                     f"{pc(s['acc_lo'])}--{pc(s['acc_hi'])} & {s['correct_exact']} & "
                     f"{s['correct_variant']} & {s['correct_unseen']} & {pval(s)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_validation.tex").write_text("\n".join(lines) + "\n", "utf-8")
    (RESULTS / "validation_facts.csv").write_text(
        "fact,value\n" + "\n".join(f"{k},{v}" for k, v in {
            "n_titles": len(titles), "n_clusters": n_clusters,
            "cluster_wilson_lo_all_correct": round(wilson(n_clusters, n_clusters)[0], 4),
            **{f"n_{s}": n_by[s] for s in STRATA},
            "n_variant_loose_lookup": n_variant_loose,
        }.items()) + "\n", "utf-8")

    for key, _, _ in TABLE + [("gemma_zeroshot", "", ""), ("gemma_fewshot", "", "")]:
        if key in by_sys:
            s = by_sys[key]
            extra = (f" | {s['n_runs']} runs: acc {s['accuracy_min']:.3f}-{s['accuracy_max']:.3f}, "
                     f"identical {s['identical_all_runs']:.3f}, Fleiss {s['fleiss_kappa_runs']:.3f}, "
                     f"p {s['mcnemar_p_min']:.2g}-{s['mcnemar_p_max']:.2g}") if s["n_runs"] > 1 else ""
            print(f"{key:22} cov {s['coverage']:.3f} acc {s['accuracy']:.3f} "
                  f"strata {s['correct_exact']}/{s['correct_variant']}/{s['correct_unseen']} "
                  f"b/c {s['mcnemar_b']}/{s['mcnemar_c']} p {s['mcnemar_p']:.3g}{extra}")
    print(Counter(e["system"] for e in error_rows))


if __name__ == "__main__":
    main()
