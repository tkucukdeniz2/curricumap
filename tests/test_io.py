import pandas as pd, pytest
from curricumap.io import load_transcript, REQUIRED_FIELDS

def test_loads_csv_with_column_mapping(tmp_path):
    src = tmp_path / "t.csv"
    pd.DataFrame({"sid": [1, 1], "ders": ["Okuma", "Yazma"], "not": [80, 70]}).to_csv(src, index=False)
    df = load_transcript(src, columns={"student_id": "sid", "course_name": "ders", "grade": "not"})
    assert list(df.columns[:3]) == ["student_id", "course_name", "grade"]
    assert df["grade"].tolist() == [80.0, 70.0]

def test_missing_required_field_raises(tmp_path):
    src = tmp_path / "t.csv"
    pd.DataFrame({"sid": [1], "ders": ["Okuma"]}).to_csv(src, index=False)
    with pytest.raises(ValueError, match="grade"):
        load_transcript(src, columns={"student_id": "sid", "course_name": "ders"})

def test_required_fields_constant():
    assert set(REQUIRED_FIELDS) == {"student_id", "course_name", "grade"}
