# src/curricumap/cli.py
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml
from .taxonomy import load_taxonomy, validate_taxonomy
from .io import load_transcript
from .classify import classify_courses
from .prepare import prepare
from .audit import audit as run_audit
from .report import write_reports
from .synth import generate

def _cmd_validate(args) -> int:
    data = yaml.safe_load(Path(args.spec).read_text("utf-8"))
    errors = validate_taxonomy(data)
    if errors:
        print("INVALID:\n  " + "\n  ".join(errors)); return 1
    print("Taxonomy is valid."); return 0

def _cmd_synth(args) -> int:
    tax = load_taxonomy(args.taxonomy)
    transcript, catalog = generate(tax, n_students=args.n_students, seed=args.seed)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    transcript.to_csv(out / "transcript.csv", index=False)
    catalog.to_csv(out / "catalog.csv", index=False)
    print(f"Wrote synthetic data to {out}"); return 0

def _cmd_run(args) -> int:
    tax = load_taxonomy(args.taxonomy)
    config = yaml.safe_load(Path(args.config).read_text("utf-8")) if args.config else {}
    columns = config.get("io", {}).get("columns")
    transcript = load_transcript(args.input, columns=columns)
    courses = transcript[["course_id", "course_name"]].drop_duplicates("course_id")
    prov = classify_courses(courses, tax)
    res = prepare(transcript, prov, config)
    data = run_audit(transcript, prov, res.wide, tax, config)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    res.wide.to_csv(out / "matrix_wide.csv")
    res.long.to_csv(out / "matrix_long.csv", index=False)
    prov.to_csv(out / "provenance.csv", index=False)
    write_reports(data, out)
    print(f"Wrote outputs to {out}"); return 0

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="curricumap")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate-taxonomy"); v.add_argument("spec"); v.set_defaults(fn=_cmd_validate)
    s = sub.add_parser("synth")
    s.add_argument("--taxonomy", required=True); s.add_argument("--out", required=True)
    s.add_argument("--n-students", type=int, default=60); s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=_cmd_synth)
    r = sub.add_parser("run")
    r.add_argument("--input", required=True); r.add_argument("--taxonomy", required=True)
    r.add_argument("--config", default=None); r.add_argument("--out", required=True)
    r.set_defaults(fn=_cmd_run)
    args = p.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
