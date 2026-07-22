from __future__ import annotations
from pathlib import Path
import pandas as pd

CANONICAL_FIELDS = ("student_id", "course_name", "grade", "course_id", "term", "date", "credits")
REQUIRED_FIELDS = ("student_id", "course_name", "grade")

def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)

def load_transcript(path: str | Path, columns: dict[str, str] | None = None) -> pd.DataFrame:
    """Load a transcript export into the canonical schema.

    `columns` maps canonical field name -> source column name. Unmapped
    canonical fields are taken as-is if already present.
    """
    raw = _read(Path(path))
    columns = columns or {}
    out = pd.DataFrame()
    for canon in CANONICAL_FIELDS:
        src = columns.get(canon, canon)
        if src in raw.columns:
            out[canon] = raw[src]
    missing = [f for f in REQUIRED_FIELDS if f not in out.columns]
    if missing:
        raise ValueError(f"Transcript missing required field(s): {', '.join(missing)}")
    out["grade"] = pd.to_numeric(out["grade"], errors="coerce")
    out["course_name"] = out["course_name"].astype(str)
    if "course_id" not in out.columns:
        out["course_id"] = out["course_name"]
    return out
