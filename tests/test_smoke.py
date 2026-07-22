import curricumap

def test_package_has_version():
    assert isinstance(curricumap.__version__, str)
    assert curricumap.__version__.count(".") >= 1
