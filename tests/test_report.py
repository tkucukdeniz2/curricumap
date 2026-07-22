# tests/test_report.py
from curricumap.report import write_reports

def test_write_reports_creates_json_and_html(tmp_path):
    data = {"taxonomy": "t", "coverage": {"n_unmapped": 0, "unmapped_courses": [],
            "n_ambiguous": 0, "domain_sizes": {"d1": 3}},
            "domains": {"d1": {"alpha": 0.8, "k": 3, "n_students": 10,
                        "mean": 70.0, "sd": 5.0, "missing_pct": 0.0}}}
    write_reports(data, tmp_path)
    assert (tmp_path / "audit.json").exists()
    html = (tmp_path / "audit.html").read_text("utf-8")
    assert "0.8" in html and "d1" in html
