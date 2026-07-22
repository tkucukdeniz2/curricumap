import curricumap

def test_package_has_version():
    assert isinstance(curricumap.__version__, str)
    assert curricumap.__version__.count(".") >= 1

def test_public_api_is_exported():
    import curricumap
    for name in ("load_taxonomy", "load_transcript", "classify_courses", "prepare", "generate"):
        assert hasattr(curricumap, name), name
