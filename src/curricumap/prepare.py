# src/curricumap/prepare.py
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass
class PrepareResult:
    wide: pd.DataFrame
    long: pd.DataFrame
    dropped: dict

def prepare(transcript: pd.DataFrame, provenance: pd.DataFrame, config: dict) -> PrepareResult:
    cfg = config.get("prepare", {})
    df = transcript.copy()
    dropped = {}

    # sentinel grades
    sent = cfg.get("sentinel_grades", {})
    if sent.get("action") == "drop" and sent.get("values"):
        before = len(df)
        df = df[~df["grade"].isin(sent["values"])]
        dropped["sentinel"] = before - len(df)

    # map course -> domain via provenance (drop unmapped)
    dmap = provenance.dropna(subset=["domain"]).set_index("course_id")["domain"]
    df["domain"] = df["course_id"].map(dmap)
    df = df.dropna(subset=["domain"])

    # dedup retakes
    dd = cfg.get("dedup", {"on": ["student_id", "course_id"], "keep": "max"})
    keep = dd.get("keep", "max")
    agg = {"max": "max", "last": "last", "mean": "mean"}[keep]
    df = (df.groupby(dd.get("on", ["student_id", "course_id"]) + ["domain"], as_index=False)
            .agg(grade=("grade", agg)))

    # aggregate to student x domain
    method = cfg.get("aggregate", {}).get("method", "mean")
    long = (df.groupby(["student_id", "domain"], as_index=False)
              .agg(grade=("grade", method)))
    wide = long.pivot(index="student_id", columns="domain", values="grade")
    wide.columns.name = None

    # coverage filter
    min_domains = cfg.get("coverage", {}).get("min_domains", 1)
    keep_students = wide.notna().sum(axis=1) >= min_domains
    dropped["low_coverage"] = int((~keep_students).sum())
    wide = wide[keep_students]
    long = long[long["student_id"].isin(wide.index)]

    return PrepareResult(wide=wide, long=long, dropped=dropped)

def reconstruct_study_year(dates: pd.Series, enroll_year: pd.Series,
                           term_boundary: str = "09-01", max_year: int = 4) -> pd.Series:
    """Map an exam date to an academic study year (1..max_year).

    An academic year starts at `term_boundary` (MM-DD). Dates on/after the
    boundary belong to the academic year starting that calendar year; earlier
    dates belong to the academic year that started the previous calendar year.
    """
    d = pd.to_datetime(dates)
    bnd_month, bnd_day = (int(x) for x in term_boundary.split("-"))
    after = (d.dt.month > bnd_month) | ((d.dt.month == bnd_month) & (d.dt.day >= bnd_day))
    academic_start = d.dt.year.where(after, d.dt.year - 1)
    year = (academic_start - enroll_year.values) + 1
    return year.clip(lower=1, upper=max_year).astype(int)
