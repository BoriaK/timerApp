from last_used import load_last_used, save_last_used

DEFAULTS = {"timer": 300, "work": 40}


def test_last_used_roundtrip(tmp_path):
    path = tmp_path / "last_used.json"
    assert load_last_used(path, DEFAULTS) == DEFAULTS  # missing file
    save_last_used(path, {"timer": 90, "work": 20})
    assert load_last_used(path, DEFAULTS) == {"timer": 90, "work": 20}


def test_last_used_ignores_bad_data(tmp_path):
    path = tmp_path / "last_used.json"
    path.write_text('{"timer": "x", "work": -5, "extra": 1}', encoding="utf-8")
    assert load_last_used(path, DEFAULTS) == DEFAULTS
    path.write_text("not json", encoding="utf-8")
    assert load_last_used(path, DEFAULTS) == DEFAULTS
    path.write_text('{"timer": true}', encoding="utf-8")
    assert load_last_used(path, DEFAULTS) == DEFAULTS
