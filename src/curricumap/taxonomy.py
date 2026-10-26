"""The taxonomy specification: locale-aware text matching, schema validation, loading."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import cached_property
from importlib import resources
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

_PKG = resources.files("curricumap")
_SCHEMA = json.loads(_PKG.joinpath("schemas", "taxonomy.schema.json").read_text("utf-8"))


def _is_turkish(language: str | None) -> bool:
    """True for a Turkish language tag: "tr" or "tur", in any case, with or without a region."""
    return (language or "und").replace("_", "-").split("-", 1)[0].lower() in {"tr", "tur"}


def locale_casefold(s: str, language: str = "und") -> str:
    """Casefold that respects Turkish dotted/dotless i.

    Text is first put in Unicode composed form (NFC), so a decomposed "I" + combining
    dot is treated as "İ". For Turkish ("tr", "tr-TR", "TR", "tur"): map İ→i and I→ı BEFORE
    casefold, so keyword matching is correct (naive casefold turns İ into i + combining dot),
    and drop any combining dot left by text that was already lower-cased without Turkish rules.
    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", s)
    if _is_turkish(language):
        s = s.replace("İ", "i").replace("I", "ı")
        return s.casefold().replace("̇", "")
    return s.casefold()


def normalize(s: str, language: str = "und") -> str:
    """Locale-casefold and collapse internal/edge whitespace."""
    return re.sub(r"\s+", " ", locale_casefold(s, language)).strip()


@dataclass(frozen=True)
class Domain:
    id: str
    label: str


@dataclass(frozen=True)
class Rule:
    domain: str
    patterns: list[str]                              # substring keywords, as written
    regex: list[str] = field(default_factory=list)   # regular expressions, as written


@dataclass(frozen=True)
class Override:
    course: str
    domain: str


@dataclass(frozen=True)
class FuzzyCfg:
    enabled: bool = False
    threshold: float = 0.9
    scorer: str = "token_set_ratio"


@dataclass(frozen=True)
class Taxonomy:
    id: str
    label: str
    language: str
    domains: list[Domain]
    rules: list[Rule]
    overrides: list[Override] = field(default_factory=list)
    fuzzy: FuzzyCfg = field(default_factory=FuzzyCfg)

    @cached_property
    def compiled_rules(self) -> list[tuple[str, list[tuple[str, str]], list[tuple[str, re.Pattern]]]]:
        """Rules in evaluation order as (domain, [(keyword, normalized)], [(regex, compiled)])."""
        return [(r.domain,
                 [(p, normalize(p, self.language)) for p in r.patterns],
                 [(x, re.compile(x)) for x in r.regex])
                for r in self.rules]


def bundled_taxonomies() -> dict[str, str]:
    """Names and labels of the taxonomies shipped with the package."""
    out = {}
    for f in sorted(_PKG.joinpath("taxonomies").iterdir(), key=lambda t: t.name):
        if f.name.endswith(".yaml"):
            out[f.name[:-5]] = yaml.safe_load(f.read_text("utf-8"))["taxonomy"]["label"]
    return out


def read_spec(path_or_name: str | Path) -> dict:
    """Parse a taxonomy YAML file; a bundled taxonomy may be given by name."""
    p = Path(path_or_name)
    if p.is_file():
        return yaml.safe_load(p.read_text("utf-8"))
    name = p.name[:-5] if p.name.endswith(".yaml") else p.name
    if str(p.parent) in ("", ".") and name in bundled_taxonomies():
        return yaml.safe_load(_PKG.joinpath("taxonomies", f"{name}.yaml").read_text("utf-8"))
    raise FileNotFoundError(f"no taxonomy file '{path_or_name}' and no bundled taxonomy of that "
                            f"name (bundled: {', '.join(bundled_taxonomies())})")


def validate_taxonomy(data: dict) -> list[str]:
    """Schema errors; for a file that fits the schema, unknown domains and invalid regexes."""
    errors = [f"{'/'.join(map(str, e.path))}: {e.message}"
              for e in Draft7Validator(_SCHEMA).iter_errors(data)]
    if errors:          # the checks below rely on the structure the schema guarantees
        return errors
    tx = data["taxonomy"]
    ids = {d["id"] for d in tx["domains"]}
    for r in tx["rules"]:
        if r["domain"] not in ids:
            errors.append(f"rule references unknown domain '{r['domain']}'")
        for x in r.get("regex", []):
            try:
                re.compile(x)
            except re.error as exc:
                errors.append(f"invalid regex '{x}': {exc}")
    for o in tx.get("overrides", []):
        if o["domain"] not in ids:
            errors.append(f"override references unknown domain '{o['domain']}'")
    return errors


def load_taxonomy(path: str | Path) -> Taxonomy:
    """Load and validate a taxonomy: a YAML file, or the name of a bundled taxonomy."""
    data = read_spec(path)
    errs = validate_taxonomy(data)
    if errs:
        raise ValueError("Invalid taxonomy spec:\n  " + "\n  ".join(errs))
    tx = data["taxonomy"]
    fz = tx.get("match", {}).get("fuzzy", {})
    return Taxonomy(
        id=tx["id"], label=tx["label"],
        language=tx.get("locale", {}).get("language", "und"),
        domains=[Domain(d["id"], d["label"]) for d in tx["domains"]],
        rules=[Rule(r["domain"], list(r.get("any", [])), list(r.get("regex", []))) for r in tx["rules"]],
        overrides=[Override(o["course"], o["domain"]) for o in tx.get("overrides", [])],
        fuzzy=FuzzyCfg(fz.get("enabled", False), fz.get("threshold", 0.9),
                       fz.get("scorer", "token_set_ratio")),
    )
