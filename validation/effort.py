"""Specification size of every taxonomy: the authoring effort a curriculum requires.

Writes results/effort.csv and results/table_effort.tex.
"""
from __future__ import annotations

import csv
from importlib import resources

import yaml

from common import HERE, RESULTS, source_courses
from curricumap import bundled_taxonomies, load_taxonomy
from curricumap.classify import assign_domain


def size(text: str) -> dict:
    tx = yaml.safe_load(text)["taxonomy"]
    rules = tx["rules"]
    return {"domains": len(tx["domains"]), "rules": len(rules),
            "keywords": sum(len(r.get("any", [])) for r in rules),
            "regexes": sum(len(r.get("regex", [])) for r in rules),
            "overrides": len(tx.get("overrides", [])),
            "yaml_lines": sum(1 for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#"))}


def keywords_only(text: str) -> dict:
    """How many official entries the ELT taxonomy assigns correctly with its regexes removed."""
    spec = yaml.safe_load(text)
    rules = [{k: v for k, v in r.items() if k != "regex"} for r in spec["taxonomy"]["rules"]]
    spec["taxonomy"]["rules"] = [r for r in rules if r.get("any")]
    path = RESULTS / "_keywords_only.yaml"
    path.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), "utf-8")
    tax = load_taxonomy(path)
    path.unlink()
    got = [(c, assign_domain(c["title"], tax).domain) for c in source_courses()]
    return {"entries": len(got), "correct": sum(d == c["domain"] for c, d in got),
            "unmatched": sum(d is None for _, d in got)}


def main() -> None:
    rows = []
    pkg = resources.files("curricumap") / "taxonomies"
    for name, label in bundled_taxonomies().items():
        rows.append({"taxonomy": name, "label": label, **size((pkg / f"{name}.yaml").read_text("utf-8"))})
    for extra in ("elt_yok_2018_v0.1.0", "elt_yok_2018_iuc_adapted"):
        p = HERE / "taxonomies" / f"{extra}.yaml"
        if p.exists():
            text = p.read_text("utf-8")
            rows.append({"taxonomy": extra, "label": yaml.safe_load(text)["taxonomy"]["label"], **size(text)})
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "effort.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lines = [r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
             r"Taxonomy & Domains & Rules & Keywords & Regexes & Overrides & YAML lines \\", r"\midrule"]
    for r in rows:
        lines.append(f"\\texttt{{{r['taxonomy'].replace('_', chr(92) + '_')}}} & {r['domains']} & {r['rules']} & "
                     f"{r['keywords']} & {r['regexes']} & {r['overrides']} & {r['yaml_lines']} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (RESULTS / "table_effort.tex").write_text("\n".join(lines) + "\n", "utf-8")
    for r in rows:
        print(r)
    kw = keywords_only((pkg / "elt_yok_2018.yaml").read_text("utf-8"))
    (RESULTS / "keywords_only.csv").write_text(
        "fact,value\n" + "".join(f"{k},{v}\n" for k, v in kw.items()), "utf-8")
    print("ELT taxonomy without its regexes:", kw)


if __name__ == "__main__":
    main()
