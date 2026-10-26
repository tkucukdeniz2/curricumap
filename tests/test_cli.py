import json
import re
import shlex
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import curricumap
from curricumap.cli import main

SAMPLE = Path(__file__).resolve().parents[1] / "examples"
PAPER = Path(__file__).resolve().parents[1] / "paper" / "main_softwarex.tex"


def test_public_api_and_version():
    for name in ("load_taxonomy", "load_transcript", "classify_courses", "prepare", "audit",
                 "write_reports", "generate", "bundled_taxonomies"):
        assert hasattr(curricumap, name), name
    assert curricumap.__version__.count(".") == 2


def test_version_flag(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert curricumap.__version__ in capsys.readouterr().out


@pytest.mark.parametrize("which", ["file", "bundled"])
def test_validate_taxonomy_ok(which, spec_path, capsys):
    spec = str(spec_path()) if which == "file" else "elt_yok_2018"
    assert main(["validate-taxonomy", spec]) == 0
    assert "valid" in capsys.readouterr().out.lower()


def test_validate_taxonomy_reports_errors(spec_path, capsys):
    bad = spec_path("taxonomy: {id: t, label: T, domains: [{id: d, label: D}], "
                    "rules: [{domain: x, any: [k]}]}\n")
    assert main(["validate-taxonomy", str(bad)]) == 1
    assert "unknown domain" in capsys.readouterr().out


def test_missing_input_is_an_error_message_not_a_traceback(tmp_path, capsys):
    rc = main(["run", "--input", str(tmp_path / "nope.csv"), "--taxonomy", "elt_yok_2018",
               "--out", str(tmp_path / "out")])
    assert rc == 2
    assert capsys.readouterr().err.startswith("error:")


def test_synth_then_run_end_to_end(spec_path, tmp_path):
    spec = str(spec_path())
    data_dir, out = tmp_path / "data", tmp_path / "out"
    assert main(["synth", "--taxonomy", spec, "--out", str(data_dir),
                 "--n-students", "20", "--seed", "1"]) == 0
    assert main(["run", "--input", str(data_dir / "transcript.csv"),
                 "--taxonomy", spec, "--out", str(out)]) == 0
    for f in ("matrix_wide.csv", "matrix_long.csv", "provenance.csv", "audit.json", "audit.html"):
        assert (out / f).exists(), f
    assert "language_skills" in json.loads((out / "audit.json").read_text("utf-8"))["domains"]


@pytest.mark.parametrize("flag", ["--n-students", "--courses-per-domain"])
@pytest.mark.parametrize("value", ["0", "abc"])
def test_synth_rejects_a_count_below_one(tmp_path, flag, value, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["synth", "--taxonomy", "elt_yok_2018", "--out", str(tmp_path / "d"), flag, value])
    assert exc.value.code == 2 and "must be a whole number of at least 1" in capsys.readouterr().err
    assert not (tmp_path / "d").exists()


def test_summary_line_uses_the_singular_for_one(tmp_path, capsys):
    src = tmp_path / "t.csv"
    src.write_text("student_id,course_name,grade\n1,Dilbilimi 1,80\n", encoding="utf-8")
    assert main(["run", "--input", str(src), "--taxonomy", "elt_yok_2018", "--out", str(tmp_path / "o")]) == 0
    assert "1 student x 1 domain; 1 course (" in capsys.readouterr().out


def test_bundled_sample_transcript_runs_as_documented(tmp_path):
    out = tmp_path / "out"
    assert main(["run", "--input", str(SAMPLE / "sample_transcript.csv"), "--taxonomy", "elt_yok_2018",
                 "--config", str(SAMPLE / "sample_config.yaml"), "--out", str(out)]) == 0
    prov = pd.read_csv(out / "provenance.csv")
    assert prov.loc[prov.course_id == "PE100", "method"].item() == "unmatched"
    assert prov["domain"].notna().sum() == 10
    wide = pd.read_csv(out / "matrix_wide.csv", index_col="student_id")
    assert wide.shape == (5, 5)
    assert wide.loc[1, "language_skills"] == 85.0          # LS101 retake 86/55 -> 86; mean(86, 84)
    assert json.loads((out / "audit.json").read_text("utf-8"))["prepare"] == {
        "sentinel": 1, "no_grade": 0, "retakes": 1, "low_coverage": 0}
    assert (out / "audit.html").read_text("utf-8").count('<tr class="small">') == 5   # 5 students: grey


def test_paper_illustrative_example_reproduces_exactly(tmp_path, monkeypatch, capsys):
    """Runs the paper's Listing 2 verbatim, in an empty directory, and pins the numbers of its
    illustrative example (Section 3)."""
    listing = re.search(r"\\begin\{lstlisting\}\[[^\]]*label=\{lst:run\}[^\]]*\]\n(.*?)\\end\{lstlisting\}",
                        PAPER.read_text("utf-8"), re.S).group(1)
    commands = [shlex.split(line) for line in listing.replace("\\\n", " ").splitlines() if line.strip()]
    assert [c[:2] for c in commands] == [["curricumap", "synth"], ["curricumap", "run"]]
    monkeypatch.chdir(tmp_path)
    for c in commands:
        assert main(c[1:]) == 0
    assert len(pd.read_csv("data/transcript.csv")) == 878
    prov = pd.read_csv("out/provenance.csv")
    assert len(prov) == 15 and (prov["method"] == "rule").all()
    a = json.loads(Path("out/audit.json").read_text("utf-8"))
    assert a["coverage"]["n_unmapped"] == 0 and a["coverage"]["n_ambiguous"] == 0
    assert pd.read_csv("out/matrix_wide.csv").shape == (60, 6)
    doms = a["domains"]
    assert list(doms) == ["language_skills", "pedagogy", "linguistics", "literature", "general_ed"]
    assert [v["k"] for v in doms.values()] == [3, 3, 3, 3, 3]
    assert [v["alpha"] for v in doms.values()] == [0.769, 0.767, 0.761, 0.819, 0.781]
    assert [v["item_missing_pct"] for v in doms.values()] == [7.8, 6.7, 8.3, 10.0, 15.0]
    assert [v["n_complete"] for v in doms.values()] == [48, 49, 45, 43, 34]
    assert capsys.readouterr().out.splitlines()[-1] == (
        "Wrote outputs to out: 60 students x 5 domains; 15 courses (0 unmapped, 0 ambiguous); "
        "dropped 0 sentinel grades, 64 retake records and 0 low-coverage students")


def test_reviewer_noise_scenario_runs_end_to_end(tmp_path):
    """Reviewer 1's scenario, seeded: five students with independent uniform grades."""
    data, out = tmp_path / "data", tmp_path / "out"
    assert main(["synth", "--taxonomy", "elt_yok_2018", "--out", str(data), "--seed", "7"]) == 0
    rs = np.random.RandomState(2026)
    rows = [(s, c, name, rs.randint(65, 100)) for s in range(1, 6)
            for c, name in pd.read_csv(data / "catalog.csv").itertuples(index=False)]
    pd.DataFrame(rows, columns=["student_id", "course_id", "course_name", "grade"]).to_csv(
        tmp_path / "noise.csv", index=False)
    assert main(["run", "--input", str(tmp_path / "noise.csv"), "--taxonomy", "elt_yok_2018",
                 "--out", str(out)]) == 0
    alphas = [v["alpha"] for v in json.loads((out / "audit.json").read_text("utf-8"))["domains"].values()]
    assert alphas == [-2.071, -0.366, 0.545, -0.124, -1.272]
    html = (out / "audit.html").read_text("utf-8")
    assert html.count('<tr class="small">') == 5           # grey, not graded: only 5 students
    assert "do not covary positively" in html and "<sup>‡</sup>Not graded" in html


def test_course_code_shared_by_two_titles_is_reported(tmp_path, capsys):
    src, out = tmp_path / "t.csv", tmp_path / "out"
    pd.DataFrame({"student_id": [1, 2, 3, 1], "course_id": ["X1", "X1", "X1", "X2"],
                  "course_name": ["İngiliz Edebiyatı 1", "Dilbilimi 1",
                                  "İNGİLİZ EDEBİYATI 1", "Dilbilimi 2"],   # a case variant: same title
                  "grade": [80, 70, 60, 75]}).to_csv(src, index=False)
    assert main(["run", "--input", str(src), "--taxonomy", "elt_yok_2018", "--out", str(out)]) == 0
    assert "X1" in capsys.readouterr().err
    assert pd.read_csv(out / "provenance.csv")["n_titles"].tolist() == [2, 1]
    cov = json.loads((out / "audit.json").read_text("utf-8"))["coverage"]
    assert cov["n_title_conflicts"] == 1
    assert cov["title_conflicts"] == [{"course_id": "X1", "titles": ["Dilbilimi 1", "İngiliz Edebiyatı 1"]}]
    assert "X1 (Dilbilimi 1 / İngiliz Edebiyatı 1)" in (out / "audit.html").read_text("utf-8")


def test_records_without_a_numeric_grade_are_reported(tmp_path, capsys):
    src, out = tmp_path / "t.csv", tmp_path / "out"
    src.write_text("student_id,course_name,grade\n1,Dilbilimi 1,80\n2,Dilbilimi 1,DZ\n", encoding="utf-8")
    assert main(["run", "--input", str(src), "--taxonomy", "elt_yok_2018", "--out", str(out)]) == 0
    assert "1 record(s) have no numeric grade" in capsys.readouterr().err
    assert json.loads((out / "audit.json").read_text("utf-8"))["prepare"]["no_grade"] == 1
    assert "1 record had no numeric grade and was ignored" in (out / "audit.html").read_text("utf-8")
