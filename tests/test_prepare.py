import re
import zipfile

import numpy as np
import pandas as pd
import pytest
import yaml

from curricumap.prepare import REQUIRED_FIELDS, load_transcript, prepare, validate_config


# --- ingest ------------------------------------------------------------------------

def test_loads_csv_with_column_mapping(tmp_path):
    src = tmp_path / "t.csv"
    pd.DataFrame({"sid": [1, 1], "ders": ["Okuma", "Yazma"], "not": [80, 70]}).to_csv(src, index=False)
    df = load_transcript(src, columns={"student_id": "sid", "course_name": "ders", "grade": "not"})
    assert list(df.columns[:3]) == ["student_id", "course_name", "grade"]
    assert df["grade"].tolist() == [80.0, 70.0]
    assert df["course_id"].tolist() == ["Okuma", "Yazma"]   # course_id defaults to the name


def test_loads_csv_with_byte_order_mark(tmp_path):
    src = tmp_path / "t.csv"
    src.write_text("student_id,course_name,grade\n1,Okuma,80\n", encoding="utf-8-sig")
    assert load_transcript(src)["student_id"].tolist() == [1]


def test_loads_xlsx(tmp_path):
    src = tmp_path / "t.xlsx"
    pd.DataFrame({"student_id": [1], "course_name": ["Okuma"], "grade": [80]}).to_excel(src, index=False)
    assert load_transcript(src)["grade"].tolist() == [80.0]


def test_legacy_xls_is_rejected_with_a_clear_message(tmp_path):
    with pytest.raises(ValueError, match=r"\.xlsx or CSV"):
        load_transcript(tmp_path / "export.xls")


def test_missing_required_field_raises(tmp_path):
    src = tmp_path / "t.csv"
    pd.DataFrame({"sid": [1], "ders": ["Okuma"]}).to_csv(src, index=False)
    with pytest.raises(ValueError, match="grade"):
        load_transcript(src, columns={"student_id": "sid", "course_name": "ders"})


def test_rows_without_student_or_course_id_are_rejected(tmp_path):
    src = tmp_path / "t.csv"   # otherwise the grouping would drop them and count them as retakes
    src.write_text("student_id,course_id,course_name,grade\n1,c1,Okuma,80\n,c1,Okuma,70\n2,,Yazma,60\n",
                   encoding="utf-8")
    with pytest.raises(ValueError, match=r"2 row\(s\) have no student_id or course_id; the first is row 3"):
        load_transcript(src)


@pytest.mark.parametrize("csv", ["student_id,course_id,course_name,grade\n1,c1,Okuma,80\n2,c1,,70\n",
                                 "student_id,course_name,grade\n1,Okuma,80\n2,,70\n"])
def test_rows_without_a_course_name_are_rejected(tmp_path, csv):
    src = tmp_path / "t.csv"   # pandas 2 would read the blank as the title "nan"; pandas 3 keeps NaN
    src.write_text(csv, encoding="utf-8")
    with pytest.raises(ValueError, match=r"1 row\(s\) have no course_name; the first is row 3"):
        load_transcript(src)


def test_a_file_named_xlsx_that_is_not_a_workbook_is_rejected(tmp_path):
    src = tmp_path / "export.xlsx"
    src.write_text("<html><table><tr><td>not a workbook</td></tr></table></html>", encoding="utf-8")
    with pytest.raises(ValueError, match=r"export\.xlsx is not an \.xlsx workbook"):
        load_transcript(src)


def test_a_zip_named_xlsx_that_holds_no_workbook_is_rejected(tmp_path):
    src = tmp_path / "export.xlsx"
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("readme.txt", "not a workbook")
    with pytest.raises(ValueError, match=r"export\.xlsx is not an \.xlsx workbook"):
        load_transcript(src)


def test_a_missing_xlsx_is_reported_as_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_transcript(tmp_path / "export.xlsx")


def test_xlsx_rows_are_numbered_as_the_sheet_shows_them(tmp_path):
    src = tmp_path / "t.xlsx"
    pd.DataFrame({"student_id": [1, 2], "course_name": ["Okuma", None], "grade": [80, 70]}).to_excel(
        src, index=False)
    with pytest.raises(ValueError, match=r"1 row\(s\) have no course_name; the first is row 3 of t\.xlsx"):
        load_transcript(src)


def test_a_csv_that_is_not_utf8_is_rejected_with_a_clear_message(tmp_path):
    src = tmp_path / "export.csv"      # e.g. saved as Windows-1254 (Turkish)
    src.write_bytes("student_id,course_name,grade\n1,Öğretim,80\n".encode("cp1254"))
    with pytest.raises(ValueError, match=r"export\.csv is not UTF-8 text"):
        load_transcript(src)


@pytest.mark.parametrize("columns, message", [
    ({"date": "Tarih"}, "io.columns.date names 'Tarih', which is not a column of t.csv"),   # optional field
    ({"grade": "Not"}, "io.columns.grade names 'Not', which is not a column of t.csv"),     # required field
])
def test_a_mapped_column_that_the_export_lacks_is_an_error(tmp_path, columns, message):
    src = tmp_path / "t.csv"   # a mistyped date mapping would otherwise order retakes by file position
    src.write_text("student_id,course_name,grade,tarih\n1,Okuma,80,2021-01-01\n", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(message)):
        load_transcript(src, columns=columns)


@pytest.mark.parametrize("csv, message", [
    ('student_id,course_name,grade\n1,Okuma,80\n\n2," ",70\n', "have no course_name; the first is row 4"),
    ("student_id,course_name,grade\n1,Okuma,80\n2, ,70\n", "have no course_name; the first is row 3"),
    ('student_id,course_id,course_name,grade\n1,c1,Okuma,80\n" ",c1,Okuma,70\n',
     "have no student_id or course_id; the first is row 3"),
    ("student_id,course_id,course_name,grade\n1,c1,Okuma,80\n\n2, ,Okuma,70\n",
     "have no student_id or course_id; the first is row 4"),
])
def test_blank_lines_are_counted_and_cells_holding_spaces_are_blank(tmp_path, csv, message):
    src = tmp_path / "t.csv"   # a spreadsheet shows the blank line, and a cell holding a space looks empty
    src.write_text(csv, encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(message)):
        load_transcript(src)


def test_numpy_sentinel_values_are_accepted():
    assert validate_config({"prepare": {"sentinel_grades": {"values": [np.int64(0), np.float64(-1)]}}})[
        "sentinels"] == [0, -1]


def test_a_numeric_xlsx_header_is_mapped_by_its_text(tmp_path):
    src = tmp_path / "t.xlsx"
    pd.DataFrame({"student_id": [1], "course_name": ["Okuma"], 2021: [80]}).to_excel(src, index=False)
    assert load_transcript(src, columns={"grade": "2021"})["grade"].tolist() == [80.0]


def test_a_semicolon_csv_with_decimal_commas_is_read(tmp_path):
    src = tmp_path / "t.csv"   # what Excel writes in a Turkish locale
    src.write_text("student_id;course_name;grade\n1;Dilbilimi 1;80\n2;Dil Edinimi;70,5\n", encoding="utf-8-sig")
    assert load_transcript(src)["grade"].tolist() == [80.0, 70.5]


def test_a_home_relative_path_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "t.csv").write_text("student_id,course_name,grade\n1,Okuma,80\n2,,70\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"the first is row 3 of t\.csv"):
        load_transcript("~/t.csv")


@pytest.mark.parametrize("before", ['"x\x00y",Okuma,80\n', f'1,{"x" * 140_000},80\n'])
def test_row_numbers_fall_back_when_csv_cannot_scan_the_file(tmp_path, before):
    src = tmp_path / "t.csv"   # pandas reads these lines; the csv module may not
    src.write_text(f"student_id,course_name,grade\n{before}2,,70\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"have no course_name; the first is row 3"):
        load_transcript(src)


def test_a_line_holding_one_quoted_empty_field_is_a_record(tmp_path):
    src = tmp_path / "t.csv"   # pandas reads '""' as an empty record, so it is counted
    src.write_text('student_id,course_name,grade\n1,Okuma,80\n""\n2,Yazma,70\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"the first is row 3"):
        load_transcript(src)


def test_required_fields_constant():
    assert set(REQUIRED_FIELDS) == {"student_id", "course_name", "grade"}


# --- cleaning and aggregation ------------------------------------------------------

PROV = pd.DataFrame({"course_id": ["c1", "c2", "c3"],
                     "course_name": ["Okuma", "Yazma", "Öğretim"],
                     "domain": ["language_skills", "language_skills", "pedagogy"]})

# student 1 retook c1 (50 then 80 -> keep max 80); a sentinel 0 on c3
TRANSCRIPT = pd.DataFrame({
    "student_id": [1, 1, 1, 1, 2, 2],
    "course_id": ["c1", "c1", "c2", "c3", "c1", "c3"],
    "course_name": ["Okuma", "Okuma", "Yazma", "Öğretim", "Okuma", "Öğretim"],
    "grade": [50, 80, 70, 0, 60, 90],
})

CFG = {"prepare": {"dedup": {"on": ["student_id", "course_id"], "keep": "max"},
                   "sentinel_grades": {"values": [0], "action": "drop"},
                   "coverage": {"min_domains": 1},
                   "aggregate": {"method": "mean"}}}


def test_dedup_keeps_max_grade():
    res = prepare(TRANSCRIPT, PROV, CFG)
    assert res.wide.loc[1, "language_skills"] == 75.0   # mean(max(50, 80), 70)


def test_dedup_last_follows_dates_not_file_order():
    t = TRANSCRIPT.assign(date=["2020-06-01", "2019-06-01", "2020-01-01", "2020-01-01",
                                "2020-01-01", "2020-01-01"])
    cfg = {"prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}}
    res = prepare(t, PROV, cfg)
    assert res.wide.loc[1, "language_skills"] == 60.0   # c1's later attempt is 50: mean(50, 70)


@pytest.mark.parametrize("dates, expected", [
    (["05.02.2020", "03.06.2020"], 75.0),   # guessed month-first, 05.02 (2 May) came after 03.06 (6 March)
    (["05.06.2021", "23.01.2020"], 60.0),   # 23.01.2020 failed month-first, became NaT and sorted last
])
def test_dedup_last_reads_dates_in_the_declared_format(dates, expected):
    t = TRANSCRIPT.assign(date=[*dates, None, None, None, None])        # student 1's c1: 50, then 80
    cfg = {"io": {"date_format": "%d.%m.%Y"}, "prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}}
    assert prepare(t, PROV, cfg).wide.loc[1, "language_skills"] == expected


def test_dedup_last_rejects_a_retake_without_a_date():
    t = TRANSCRIPT.assign(date=["2019-06-01", None, None, None, None, None])   # c1 retake undated
    with pytest.raises(ValueError, match=r"cannot order a retake without a date \(student 1, course c1\)"):
        prepare(t, PROV, {"prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}})


def test_dedup_last_rejects_a_date_that_does_not_match_the_format():
    t = TRANSCRIPT.assign(date=["05.06.2021", "23.01.2020", None, None, None, None])
    with pytest.raises(ValueError, match=r"date '05\.06\.2021' does not match io\.date_format 'ISO8601'"):
        prepare(t, PROV, {"prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}})


def test_dedup_last_gives_the_dotted_date_hint_only_when_no_format_is_declared():
    t = TRANSCRIPT.assign(date=["2021-01-05", "2021-06-01", None, None, None, None])
    cfg = {"io": {"date_format": "%d.%m.%Y"}, "prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}}
    with pytest.raises(ValueError, match="does not match io.date_format '%d.%m.%Y'") as exc:
        prepare(t, PROV, cfg)
    assert "for dates such as" not in str(exc.value)


def test_dedup_last_needs_no_date_for_attempts_that_dedup_on_keeps_apart():
    t = TRANSCRIPT.assign(date=["2020-01-01", None, None, None, None, None])   # c1: dated 50, undated 80
    res = prepare(t, PROV, {"prepare": {**CFG["prepare"], "dedup": {"on": ["date"], "keep": "last"}}})
    assert res.wide.loc[1, "language_skills"] == pytest.approx((50 + 80 + 70) / 3)
    assert res.dropped["retakes"] == 0


@pytest.mark.parametrize("keep, grades, expected", [
    ("mean", [50, 80, 70, 0, 60, 90], 67.5),   # mean(mean(50, 80), 70)
    ("last", [80, 50, 70, 0, 60, 90], 60.0),   # no date column: the later row in the file (50), not the max
])
def test_dedup_keep_mean_and_last_without_a_date_column(keep, grades, expected):
    cfg = {"prepare": {**CFG["prepare"], "dedup": {"keep": keep}}}
    assert prepare(TRANSCRIPT.assign(grade=grades), PROV, cfg).wide.loc[1, "language_skills"] == expected


def test_aggregate_median():
    t = pd.DataFrame({"student_id": [1, 1, 1], "course_id": ["c1", "c2", "c3"],
                      "course_name": ["Okuma", "Yazma", "Öğretim"], "grade": [10, 20, 90]})
    res = prepare(t, PROV.assign(domain="language_skills"), {"prepare": {"aggregate": {"method": "median"}}})
    assert res.wide.loc[1, "language_skills"] == 20.0      # the mean would be 40


@pytest.mark.parametrize("date", [" ", "2021-06-01 "])
def test_dedup_last_strips_text_dates(date):
    t = TRANSCRIPT.assign(date=["2020-01-01", "2021-01-01", date, None, None, None])  # c2 is not retaken
    res = prepare(t, PROV, {"prepare": {**CFG["prepare"], "dedup": {"keep": "last"}}})
    assert res.wide.loc[1, "language_skills"] == 75.0       # c1's later attempt (80) and c2 (70)


def test_prepare_without_course_id_names_the_column():
    t = pd.DataFrame({"student_id": [1], "course_name": ["Okuma"], "grade": [80]})
    with pytest.raises(ValueError, match="the transcript has no course_id column"):
        prepare(t, PROV, {})


def test_dedup_on_date_keeps_attempts_apart_and_loses_no_row():
    t = TRANSCRIPT.assign(date=["2019-06-01", "2020-06-01", None, None, None, None])
    res = prepare(t, PROV, {"prepare": {"dedup": {"on": ["date"]}}})
    assert res.wide.loc[1, "language_skills"] == pytest.approx((50 + 80 + 70) / 3)
    assert res.wide.loc[2, "pedagogy"] == 90.0               # rows without a date are kept
    assert res.dropped == {"sentinel": 0, "no_grade": 0, "retakes": 0, "low_coverage": 0}


def test_dedup_on_a_field_the_transcript_lacks_is_an_error():
    with pytest.raises(ValueError, match="prepare.dedup.on names 'date'"):
        prepare(TRANSCRIPT, PROV, {"prepare": {"dedup": {"on": ["student_id", "course_id", "date"]}}})


def test_sentinel_zero_dropped_from_domain_mean():
    res = prepare(TRANSCRIPT, PROV, CFG)
    assert pd.isna(res.wide.loc[1, "pedagogy"])          # student 1's only pedagogy grade was 0
    assert res.wide.loc[2, "pedagogy"] == 90.0


def test_prepare_reports_what_cleaning_dropped():
    assert prepare(TRANSCRIPT, PROV, CFG).dropped == {"sentinel": 1, "no_grade": 0, "retakes": 1,
                                                      "low_coverage": 0}
    # without a sentinel value the zero is an ordinary grade; the c1 retake is merged either way
    assert prepare(TRANSCRIPT, PROV, {}).dropped == {"sentinel": 0, "no_grade": 0, "retakes": 1,
                                                    "low_coverage": 0}


def test_records_without_a_numeric_grade_are_counted_not_merged(tmp_path):
    src = tmp_path / "t.csv"
    src.write_text("student_id,course_id,course_name,grade\n1,c1,Okuma,80\n1,c1,Okuma,DZ\n"
                   "1,c2,Yazma,\n2,c1,Okuma,70\n", encoding="utf-8")
    t = load_transcript(src)                       # "DZ" (an absence code) and the blank become NaN
    prov = pd.DataFrame({"course_id": ["c1", "c2"], "domain": ["language_skills", "language_skills"]})
    res = prepare(t, prov, {})
    assert res.dropped == {"sentinel": 0, "no_grade": 2, "retakes": 0, "low_coverage": 0}
    assert res.wide["language_skills"].tolist() == [80.0, 70.0]


def test_students_without_any_usable_grade_are_counted_as_low_coverage():
    t = pd.concat([TRANSCRIPT, pd.DataFrame({"student_id": [3], "course_id": ["c3"],
                                             "course_name": ["Öğretim"], "grade": [0]})])
    res = prepare(t, PROV, CFG)                      # student 3's only grade is a sentinel
    assert 3 not in res.wide.index and res.dropped["low_coverage"] == 1


@pytest.mark.parametrize("course_id, grade, no_grade", [
    ("c9", 75, 0),              # a course that no rule maps
    ("c1", float("nan"), 1),    # no numeric grade
])
def test_students_left_without_a_mapped_grade_are_counted_as_low_coverage(course_id, grade, no_grade):
    t = pd.concat([TRANSCRIPT, pd.DataFrame({"student_id": [3], "course_id": [course_id],
                                             "course_name": ["Almanca"], "grade": [grade]})])
    res = prepare(t, PROV, CFG)
    assert 3 not in res.wide.index
    assert res.dropped == {"sentinel": 1, "no_grade": no_grade, "retakes": 1, "low_coverage": 1}


def test_coverage_filter_drops_students_below_min_domains():
    cfg = {"prepare": {**CFG["prepare"], "coverage": {"min_domains": 2}}}
    res = prepare(TRANSCRIPT, PROV, cfg)
    assert list(res.wide.index) == [2]
    assert res.dropped["low_coverage"] == 1
    assert set(res.long["student_id"]) == {2}


@pytest.mark.parametrize("bad, message", [
    ({"prepare": {"dedup": {"keep": "first"}}}, "prepare.dedup.keep must be one of"),
    ({"prepare": {"aggregate": {"method": "sum"}}}, "prepare.aggregate.method must be one of"),
    ({"prepare": {"sentinel_grades": {"values": [0], "action": "keep"}}}, "prepare.sentinel_grades.action"),
    ({"prepare": {"coverage": {"min_domains": 0}}}, "prepare.coverage.min_domains must be"),
    ({"audit": {"cronbach": {"missing": "colum_mean"}}}, "audit.cronbach.missing must be one of"),
    # unknown keys at every level
    ({"output": {}}, "unknown run-config key 'output'"),
    ({"io": {"column": {}}}, "unknown run-config key 'io.column'"),
    ({"prepare": {"sentinels": {"values": [0]}}}, "unknown run-config key 'prepare.sentinels'"),
    ({"prepare": {"dedup": {"by": ["date"]}}}, "unknown run-config key 'prepare.dedup.by'"),
    ({"prepare": {"sentinel_grades": {"value": [0]}}}, "unknown run-config key 'prepare.sentinel_grades.value'"),
    ({"prepare": {"coverage": {"min_domain": 3}}}, "unknown run-config key 'prepare.coverage.min_domain'"),
    ({"prepare": {"aggregate": {"how": "mean"}}}, "unknown run-config key 'prepare.aggregate.how'"),
    ({"audit": {"alpha": {}}}, "unknown run-config key 'audit.alpha'"),
    ({"audit": {"cronbach": {"method": "pairwise"}}}, "unknown run-config key 'audit.cronbach.method'"),
    ({"io": {"columns": {"dates": "Tarih"}}}, "unknown run-config key 'io.columns.dates'"),
    ({"io": {"columns": {"term": "Donem"}}}, "unknown run-config key 'io.columns.term'"),
    ({"prepare": None}, "prepare must be a mapping"),
    # YAML 1.1 reads an unquoted `on` as the boolean True
    (yaml.safe_load("prepare:\n  dedup: { on: [student_id, course_id] }\n"), 'write "on":'),
    # values of the wrong type
    ({"io": {"columns": ["student_id"]}}, "io.columns must be a mapping"),
    ({"io": {"columns": {"grade": ["not"]}}}, "io.columns must map transcript fields to column names"),
    ({"io": {"date_format": ["%d.%m.%Y"]}}, "io.date_format must be a date format"),
    ({"prepare": {"dedup": {"on": "student_id"}}}, "prepare.dedup.on must list transcript fields"),
    ({"prepare": {"dedup": {"on": ["student_id", "course_id", "term"]}}}, "prepare.dedup.on must list"),
    ({"prepare": {"sentinel_grades": {"values": 0}}}, "prepare.sentinel_grades.values must be a list"),
    ({"prepare": {"sentinel_grades": {"values": [float("nan")]}}}, "prepare.sentinel_grades.values must be"),
    ({"prepare": {"sentinel_grades": {"values": [True]}}}, "prepare.sentinel_grades.values must be"),
    ({"prepare": {"sentinel_grades": {"values": [float("inf")]}}}, "prepare.sentinel_grades.values must be"),
    ({"prepare": {"sentinel_grades": {"values": [10 ** 400]}}}, "prepare.sentinel_grades.values must be"),
    ({"io": {"columns": {"grade": 2021}}}, 'quote names that YAML reads as numbers or booleans'),
    ({"prepare": {"coverage": {"min_domains": True}}}, "prepare.coverage.min_domains must be"),
])
def test_invalid_config_is_rejected(bad, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        validate_config(bad)


def test_config_defaults():
    assert validate_config(None) == {"columns": {}, "date_format": "ISO8601", "on": [], "keep": "max",
                                     "sentinels": [], "min_domains": 1, "method": "mean",
                                     "missing": "column_mean"}


def test_config_with_every_option_is_accepted():
    s = validate_config({"io": {"columns": {"student_id": "sid"}, "date_format": "%d.%m.%Y"},
                         "prepare": {**CFG["prepare"], "dedup": {"on": ["student_id"], "keep": "last"}},
                         "audit": {"cronbach": {"missing": "pairwise"}}})
    assert s == {"columns": {"student_id": "sid"}, "date_format": "%d.%m.%Y", "on": ["student_id"],
                 "keep": "last", "sentinels": [0], "min_domains": 1, "method": "mean", "missing": "pairwise"}
