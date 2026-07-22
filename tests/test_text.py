from curricumap.text import locale_casefold, normalize

def test_turkish_dotted_capital_i_becomes_plain_i():
    # naive .casefold() gives "i̇ngilizce" (i + combining dot); locale must give "ingilizce"
    assert locale_casefold("İngilizce", "tr") == "ingilizce"
    assert "İngilizce".casefold() != "ingilizce"  # proves the naive path is wrong

def test_turkish_dotless_capital_i_becomes_dotless():
    assert locale_casefold("ISI", "tr") == "ısı"
    assert "ISI".lower() == "isi"  # proves naive path is wrong

def test_default_language_uses_standard_casefold():
    assert locale_casefold("READING", "und") == "reading"

def test_normalize_collapses_whitespace_and_casefolds():
    assert normalize("  Öğretim   Yöntemleri ", "tr") == "öğretim yöntemleri"
