"""Ingest a registrar export, clean the grade records, aggregate to a student-by-domain matrix."""
from __future__ import annotations

import csv
import math
import numbers
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CANONICAL_FIELDS = ("student_id", "course_name", "grade", "course_id", "date")
REQUIRED_FIELDS = ("student_id", "course_name", "grade")
DEDUP_ON = ("student_id", "course_id", "course_name", "date")
DEDUP_KEEP = ("max", "last", "mean")
AGGREGATE_METHODS = ("mean", "median")
CRONBACH_MISSING = ("column_mean", "listwise", "pairwise")
# Run-config sections and the keys allowed in each ("" is the top level).
CONFIG_KEYS = {"": {"io", "prepare", "audit"}, "io": {"columns", "date_format"},
               "io.columns": set(CANONICAL_FIELDS),
               "prepare": {"dedup", "sentinel_grades", "coverage", "aggregate"},
               "prepare.dedup": {"on", "keep"}, "prepare.sentinel_grades": {"values", "action"},
               "prepare.coverage": {"min_domains"}, "prepare.aggregate": {"method"},
               "audit": {"cronbach"}, "audit.cronbach": {"missing"}}


def _read(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".xls":
        raise ValueError(f"{path.name}: legacy .xls is not supported; save the export as .xlsx or CSV")
    if suffix == ".xlsx":
        try:
            return pd.read_excel(path, engine="openpyxl")
        except OSError:                # file access: missing, unreadable, not a directory, ...
            raise
        except Exception as exc:     # a renamed .xls, an HTML "Excel" export, a zip that holds no workbook
            raise ValueError(f"{path.name} is not an .xlsx workbook; save the export as .xlsx or CSV "
                             f"({type(exc).__name__}: {exc})") from exc
    try:
        return pd.read_csv(path, encoding="utf-8-sig", **_csv_dialect(path))
    except UnicodeDecodeError as exc:   # text in another encoding, or a workbook such as .xlsm or .ods
        raise ValueError(f"{path.name} is not UTF-8 text; save the export as CSV (UTF-8) or .xlsx "
                         f"({exc})") from exc


def _csv_dialect(path: Path) -> dict:
    """Excel in a locale with a decimal comma (e.g. Turkish) saves CSV with semicolons;
    read such a file with ';' between fields and ',' as the decimal mark."""
    try:
        with path.open(encoding="utf-8-sig") as fh:
            header = fh.readline()
    except (OSError, UnicodeError):    # let pandas report it, or read a compressed file
        return {}
    return {"sep": ";", "decimal": ","} if ";" in header and "," not in header else {}


def _row(path: Path, position: int) -> int:
    """The line of the file, counting the header and any blank lines, that holds the data
    record read at `position` (pandas skips blank lines; a spreadsheet shows them).
    """
    if path.suffix.lower() == ".xlsx":
        return position + 2
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = [i for i, rec in enumerate(csv.reader(fh, **_reader_dialect(path)), start=1)
                    if not (rec == [] or (len(rec) == 1 and rec[0] != "" and not rec[0].strip(" \t")))]
    except (csv.Error, OSError, UnicodeError):     # a file pandas reads but csv does not: count records
        return position + 2
    return rows[position + 1] if position + 1 < len(rows) else position + 2


def _reader_dialect(path: Path) -> dict:
    return {"delimiter": ";"} if _csv_dialect(path) else {}


def _blank(col: pd.Series) -> pd.Series:
    """Missing, or text that is only whitespace (a cell holding a space looks empty)."""
    blank = col.isna()
    if not pd.api.types.is_numeric_dtype(col):      # text (str or object dtype); test each value once
        empty = [v for v in col.unique() if isinstance(v, str) and not v.strip()]
        if empty:
            blank |= col.isin(empty)
    return blank


def load_transcript(path: str | Path, columns: dict[str, str] | None = None) -> pd.DataFrame:
    """Load a transcript export into the canonical schema.

    `columns` maps canonical field name -> source column name; a mapped column that the
    file does not have is an error. Unmapped canonical fields are taken as-is if present.
    """
    path = Path(path).expanduser()
    raw = _read(path)
    raw.columns = raw.columns.map(str)        # a numeric header cell in .xlsx is mapped by its text
    columns = columns or {}
    for canon, src in columns.items():
        if src not in raw.columns:
            raise ValueError(f"io.columns.{canon} names {src!r}, which is not a column of {path.name} "
                             f"(its columns: {', '.join(map(repr, raw.columns))})")
    out = pd.DataFrame()
    for canon in CANONICAL_FIELDS:
        src = columns.get(canon, canon)
        if src in raw.columns:
            out[canon] = raw[src]
    missing = [f for f in REQUIRED_FIELDS if f not in out.columns]
    if missing:
        raise ValueError(f"Transcript missing required field(s): {', '.join(missing)}")
    out["grade"] = pd.to_numeric(out["grade"], errors="coerce")
    no_title = _blank(out["course_name"])     # before astype(str), which turns a blank into "nan"
    if no_title.any():
        raise ValueError(f"{int(no_title.sum())} row(s) have no course_name; the first is row "
                         f"{_row(path, int(no_title.to_numpy().argmax()))} of {path.name}, counting the header")
    out["course_name"] = out["course_name"].astype(str)
    if "course_id" not in out.columns:
        out["course_id"] = out["course_name"]
    blank = _blank(out["student_id"]) | _blank(out["course_id"])
    if blank.any():
        raise ValueError(f"{int(blank.sum())} row(s) have no student_id or course_id; the first is row "
                         f"{_row(path, int(blank.to_numpy().argmax()))} of {path.name}, counting the header")
    return out


def _check_keys(section, path: str = "") -> None:
    if not isinstance(section, dict):
        raise ValueError(f"{path or 'the run-config'} must be a mapping, got {section!r}")
    for key, value in section.items():
        if not isinstance(key, str):
            raise ValueError(f"{path or 'run-config'}: key {key!r} is not a string (YAML reads an unquoted "
                             'on: as true; write "on":)')
        where = f"{path}.{key}" if path else key
        if key not in CONFIG_KEYS[path]:
            raise ValueError(f"unknown run-config key '{where}' "
                             f"(allowed: {', '.join(sorted(CONFIG_KEYS[path]))})")
        if where in CONFIG_KEYS:
            _check_keys(value, where)


def validate_config(config: dict | None) -> dict:
    """Check a run-config and return its settings, with the defaults filled in.

    Raises ValueError for an unknown key or an unsupported value.
    """
    config = config or {}
    _check_keys(config)
    p = config.get("prepare", {})
    s = {"columns": config.get("io", {}).get("columns", {}),
         "date_format": config.get("io", {}).get("date_format", "ISO8601"),
         "on": p.get("dedup", {}).get("on", []),
         "keep": p.get("dedup", {}).get("keep", "max"),
         "sentinels": p.get("sentinel_grades", {}).get("values", []),
         "min_domains": p.get("coverage", {}).get("min_domains", 1),
         "method": p.get("aggregate", {}).get("method", "mean"),
         "missing": config.get("audit", {}).get("cronbach", {}).get("missing", "column_mean")}
    if not all(isinstance(v, str) for v in s["columns"].values()):
        raise ValueError(f"io.columns must map transcript fields to column names, got {s['columns']!r} "
                         '(quote names that YAML reads as numbers or booleans, such as "2021" or "No")')
    if not isinstance(s["date_format"], str):
        raise ValueError(f"io.date_format must be a date format such as '%d.%m.%Y', got {s['date_format']!r}")
    if not isinstance(s["on"], list) or not all(f in DEDUP_ON for f in s["on"]):
        raise ValueError(f"prepare.dedup.on must list transcript fields ({', '.join(DEDUP_ON)}), "
                         f"got {s['on']!r}")
    if s["keep"] not in DEDUP_KEEP:
        raise ValueError(f"prepare.dedup.keep must be one of {DEDUP_KEEP}, got {s['keep']!r}")
    if not isinstance(s["sentinels"], list) or not all(_is_grade(g) for g in s["sentinels"]):
        raise ValueError(f"prepare.sentinel_grades.values must be a list of grades, got {s['sentinels']!r}")
    action = p.get("sentinel_grades", {}).get("action", "drop")
    if action != "drop":
        raise ValueError(f"prepare.sentinel_grades.action must be 'drop', got {action!r}")
    if isinstance(s["min_domains"], bool) or not isinstance(s["min_domains"], int) or s["min_domains"] < 1:
        raise ValueError(f"prepare.coverage.min_domains must be a positive integer, got {s['min_domains']!r}")
    if s["method"] not in AGGREGATE_METHODS:
        raise ValueError(f"prepare.aggregate.method must be one of {AGGREGATE_METHODS}, got {s['method']!r}")
    if s["missing"] not in CRONBACH_MISSING:
        raise ValueError(f"audit.cronbach.missing must be one of {CRONBACH_MISSING}, got {s['missing']!r}")
    return s


def _is_grade(g) -> bool:
    """A finite real number that is not a boolean (YAML reads true/false as booleans)."""
    if not isinstance(g, numbers.Real) or isinstance(g, bool):
        return False
    try:
        return math.isfinite(g)
    except OverflowError:              # an integer too large for a float
        return False


def clean_grades(transcript: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Drop sentinel grades and records without a numeric grade, then merge retakes into one
    grade per student and course.

    Both prepare() and audit() call this, so the reliability statistics describe
    exactly the grades that produced the matrix.
    """
    s = validate_config(config)
    df = transcript[~transcript["grade"].isin(s["sentinels"])] if s["sentinels"] else transcript
    df = df[df["grade"].notna()]       # blank, or text such as an absence code (load_transcript coerces)
    if "course_id" not in df.columns:
        raise ValueError("the transcript has no course_id column (load_transcript fills it from course_name)")
    on = list(dict.fromkeys(["student_id", "course_id", *s["on"]]))
    absent = [f for f in on if f not in df.columns]
    if absent:
        raise ValueError(f"prepare.dedup.on names '{absent[0]}', which the transcript does not have")
    if s["keep"] == "last" and "date" in df.columns:
        # text dates are stripped, and a cell holding only spaces is an empty date
        raw = df["date"].map(lambda v: (v.strip() or None) if isinstance(v, str) else v)
        d = pd.to_datetime(raw, format=s["date_format"], errors="coerce")
        bad = d.isna() & raw.notna()
        if bad.any():
            hint = " (for dates such as 23.06.2020, use '%d.%m.%Y')" if s["date_format"] == "ISO8601" else ""
            raise ValueError(f"date {raw[bad].iloc[0]!r} does not match io.date_format "
                             f"{s['date_format']!r}{hint}")
        retaken = df.duplicated(on, keep=False)       # records that the dedup below merges
        if (d.isna() & retaken).any():
            row = df[d.isna() & retaken].iloc[0]
            raise ValueError(f"dedup.keep: last cannot order a retake without a date (student "
                             f"{row['student_id']}, course {row['course_id']})")
        df = df.assign(_d=d).sort_values("_d", kind="stable")
    return df.groupby(on, as_index=False, dropna=False).agg(grade=("grade", s["keep"]))


@dataclass
class PrepareResult:
    wide: pd.DataFrame
    long: pd.DataFrame
    dropped: dict


def prepare(transcript: pd.DataFrame, provenance: pd.DataFrame, config: dict) -> PrepareResult:
    s = validate_config(config)
    n_sentinel = int(transcript["grade"].isin(s["sentinels"]).sum())
    n_no_grade = int(transcript["grade"].isna().sum())

    df = clean_grades(transcript, config)
    n_retakes = len(transcript) - n_sentinel - n_no_grade - len(df)    # merged into another by dedup
    dmap = provenance.dropna(subset=["domain"]).set_index("course_id")["domain"]
    df["domain"] = df["course_id"].map(dmap)
    df = df.dropna(subset=["domain"])

    long = df.groupby(["student_id", "domain"], as_index=False).agg(grade=("grade", s["method"]))
    wide = long.pivot(index="student_id", columns="domain", values="grade")
    wide.columns.name = None

    keep_students = wide.notna().sum(axis=1) >= s["min_domains"]
    wide = wide[keep_students]
    long = long[long["student_id"].isin(wide.index)]
    # students left out of the matrix: below the minimum, or with no usable grade in any domain
    n_low = int(transcript["student_id"].nunique() - len(wide))
    return PrepareResult(wide=wide, long=long,
                         dropped={"sentinel": n_sentinel, "no_grade": n_no_grade, "retakes": n_retakes,
                                  "low_coverage": n_low})
