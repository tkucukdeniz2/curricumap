"""Shared paths and helpers for the classification validation (see validation/README.md)."""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
PRED = HERE / "results" / "predictions"
RESULTS = HERE / "results"
DOMAINS = ["language_skills", "pedagogy", "linguistics", "literature", "general_ed"]
ABSTAIN = "unmatched"


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def source_courses() -> list[dict]:
    """The 158 official YOK programme titles with their convention labels (authoring source)."""
    return read_csv(DATA / "yok_programmes.csv")


def target_courses() -> list[dict]:
    """The 143 registrar titles of the held-out institution with reference labels."""
    return read_csv(DATA / "iuc_elt_catalog.csv")


def definitions() -> str:
    return (HERE / "prompts" / "definitions.md").read_text("utf-8").strip()


def write_predictions(system: str, run: int, rows: list[dict]) -> Path:
    """rows: dicts with title, predicted (a domain or ABSTAIN) and optional detail."""
    PRED.mkdir(parents=True, exist_ok=True)
    path = PRED / f"{system}__run{run}.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["title", "predicted", "detail"])
        w.writeheader()
        for r in rows:
            w.writerow({"title": r["title"], "predicted": r["predicted"], "detail": r.get("detail", "")})
    return path
