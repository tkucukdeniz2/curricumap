import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from curricumap.taxonomy import load_taxonomy  # noqa: E402

MINI = """
taxonomy:
  id: t
  label: T
  locale: { language: tr, casefold: locale-aware }
  domains: [{id: language_skills, label: LS}, {id: pedagogy, label: Ped}]
  rules: [{domain: language_skills, any: ["okuma"]}, {domain: pedagogy, any: ["öğretim"]}]
"""


@pytest.fixture
def spec_path(tmp_path):
    """Write a taxonomy YAML (default: a two-domain Turkish spec) and return its path."""
    def _write(text=MINI, name="t.yaml"):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p
    return _write


@pytest.fixture
def make_tax(spec_path):
    return lambda text=MINI: load_taxonomy(spec_path(text))
