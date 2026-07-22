# src/curricumap/report.py
from __future__ import annotations
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_ENV = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
                   autoescape=True)

def write_reports(audit_data: dict, out_dir: str | Path) -> None:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), "utf-8")
    html = _ENV.get_template("audit.html.j2").render(a=audit_data)
    (out / "audit.html").write_text(html, "utf-8")
