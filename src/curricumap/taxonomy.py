# src/curricumap/taxonomy.py
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from jsonschema import Draft7Validator

_SCHEMA = json.loads((Path(__file__).parent / "schemas" / "taxonomy.schema.json").read_text("utf-8"))

@dataclass(frozen=True)
class Domain: id: str; label: str
@dataclass(frozen=True)
class Rule: domain: str; patterns: list[str]
@dataclass(frozen=True)
class Override: course: str; domain: str
@dataclass(frozen=True)
class FuzzyCfg: enabled: bool = False; threshold: float = 0.9; scorer: str = "token_set_ratio"

@dataclass(frozen=True)
class Taxonomy:
    id: str; label: str; language: str; casefold: str
    domains: list[Domain]; rules: list[Rule]
    overrides: list[Override] = field(default_factory=list)
    fuzzy: FuzzyCfg = field(default_factory=FuzzyCfg)
    unmatched: str = "flag"
    @property
    def domain_ids(self) -> set[str]:
        return {d.id for d in self.domains}

def validate_taxonomy(data: dict) -> list[str]:
    errors = [f"{'/'.join(map(str, e.path))}: {e.message}"
              for e in Draft7Validator(_SCHEMA).iter_errors(data)]
    tx = data.get("taxonomy", {})
    ids = {d.get("id") for d in tx.get("domains", [])}
    for r in tx.get("rules", []):
        if r.get("domain") not in ids:
            errors.append(f"rule references unknown domain '{r.get('domain')}'")
    for o in tx.get("overrides", []):
        if o.get("domain") not in ids:
            errors.append(f"override references unknown domain '{o.get('domain')}'")
    return errors

def load_taxonomy(path: str | Path) -> Taxonomy:
    data = yaml.safe_load(Path(path).read_text("utf-8"))
    errs = validate_taxonomy(data)
    if errs:
        raise ValueError("Invalid taxonomy spec:\n  " + "\n  ".join(errs))
    tx = data["taxonomy"]
    locale = tx.get("locale", {})
    match = tx.get("match", {})
    fz = match.get("fuzzy", {})
    return Taxonomy(
        id=tx["id"], label=tx["label"],
        language=locale.get("language", "und"),
        casefold=locale.get("casefold", "locale-aware"),
        domains=[Domain(d["id"], d["label"]) for d in tx["domains"]],
        rules=[Rule(r["domain"], list(r["any"])) for r in tx["rules"]],
        overrides=[Override(o["course"], o["domain"]) for o in tx.get("overrides", [])],
        fuzzy=FuzzyCfg(fz.get("enabled", False), fz.get("threshold", 0.9),
                       fz.get("scorer", "token_set_ratio")),
        unmatched=tx.get("defaults", {}).get("unmatched", "flag"),
    )
