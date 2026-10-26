"""Command-line interface: validate-taxonomy, synth, run."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import __version__
from .audit import audit, write_reports
from .classify import classify_courses
from .prepare import load_transcript, prepare, validate_config
from .synth import generate
from .taxonomy import bundled_taxonomies, load_taxonomy, read_spec, validate_taxonomy


def _n(k: int, one: str, many: str | None = None) -> str:
    return f"{k} {one if k == 1 else (many or one + 's')}"


def _positive_int(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be a whole number of at least 1, got {value}")
    return n


def _cmd_validate(args) -> int:
    errors = validate_taxonomy(read_spec(args.spec))
    if errors:
        print("INVALID:\n  " + "\n  ".join(errors))
        return 1
    print("Taxonomy is valid.")
    return 0


def _cmd_synth(args) -> int:
    tax = load_taxonomy(args.taxonomy)
    transcript, catalog = generate(tax, n_students=args.n_students, seed=args.seed,
                                   courses_per_domain=args.courses_per_domain)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    transcript.to_csv(out / "transcript.csv", index=False)
    catalog.to_csv(out / "catalog.csv", index=False)
    print(f"Wrote synthetic data to {out}")
    return 0


def _cmd_run(args) -> int:
    tax = load_taxonomy(args.taxonomy)
    config = (yaml.safe_load(Path(args.config).read_text("utf-8")) or {}) if args.config else {}
    transcript = load_transcript(args.input, columns=validate_config(config)["columns"])
    prov = classify_courses(transcript[["course_id", "course_name"]], tax)
    res = prepare(transcript, prov, config)
    data = audit(transcript, prov, res.wide, tax, config, dropped=res.dropped)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res.wide.to_csv(out / "matrix_wide.csv")
    res.long.to_csv(out / "matrix_long.csv", index=False)
    prov.to_csv(out / "provenance.csv", index=False)
    write_reports(data, out)
    cov, drop = data["coverage"], res.dropped
    if cov["n_title_conflicts"]:
        print(f"warning: course_id used for several titles, classified by the first: "
              f"{', '.join(c['course_id'] for c in cov['title_conflicts'])} "
              f"(see coverage.title_conflicts in audit.json)", file=sys.stderr)
    if drop["no_grade"]:
        print(f"warning: {drop['no_grade']} record(s) have no numeric grade (blank, or text such as an "
              f"absence code) and were ignored (see prepare.no_grade in audit.json)", file=sys.stderr)
    print(f"Wrote outputs to {out}: {_n(len(res.wide), 'student')} x {_n(res.wide.shape[1], 'domain')}; "
          f"{_n(len(prov), 'course')} ({cov['n_unmapped']} unmapped, {cov['n_ambiguous']} ambiguous); "
          f"dropped {_n(drop['sentinel'], 'sentinel grade')}, {_n(drop['retakes'], 'retake record')} and "
          f"{_n(drop['low_coverage'], 'low-coverage student')}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="curricumap", description=(
        "Turn registrar transcripts into auditable student-by-domain matrices. "
        f"Bundled taxonomies: {', '.join(bundled_taxonomies())}."))
    p.add_argument("--version", action="version", version=f"curricumap {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate-taxonomy", help="check a taxonomy file or bundled name")
    v.add_argument("spec")
    v.set_defaults(fn=_cmd_validate)
    s = sub.add_parser("synth", help="write a seeded synthetic transcript and catalog")
    s.add_argument("--taxonomy", required=True, help="YAML file or bundled taxonomy name")
    s.add_argument("--out", required=True)
    s.add_argument("--n-students", type=_positive_int, default=60)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--courses-per-domain", type=_positive_int, default=3)
    s.set_defaults(fn=_cmd_synth)
    r = sub.add_parser("run", help="classify, clean, aggregate and audit a transcript")
    r.add_argument("--input", required=True, help="transcript export (.csv or .xlsx)")
    r.add_argument("--taxonomy", required=True, help="YAML file or bundled taxonomy name")
    r.add_argument("--config", default=None, help="optional run-config YAML")
    r.add_argument("--out", required=True)
    r.set_defaults(fn=_cmd_run)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
