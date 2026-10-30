from presets import (DEFAULT_PRESETS, add_preset, delete_preset, describe,
                     load_presets, save_presets)


def test_first_run_gets_defaults_and_roundtrip(tmp_path):
    path = tmp_path / "p.json"
    assert load_presets(path) == DEFAULT_PRESETS
    items = add_preset([], "Mine", 30, 15, 4)
    save_presets(path, items)
    assert load_presets(path) == items


def test_corrupt_file_gives_empty_list_and_bad_entries_dropped(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("nope")
    assert load_presets(path) == []
    path.write_text('{"a": 1}')
    assert load_presets(path) == []
    path.write_text('[{"name": "ok", "work": 5, "rest": 0, "rounds": 1},'
                    '{"name": "", "work": 5, "rest": 0, "rounds": 1},'
                    '{"name": "bad", "work": 0, "rest": 0, "rounds": 1},'
                    '{"name": "x"}, 7]')
    assert [p["name"] for p in load_presets(path)] == ["ok"]


def test_add_replaces_same_name_and_validates():
    items = add_preset([], "Tabata", 20, 10, 8)
    items = add_preset(items, "  tabata ", 30, 5, 6)  # same name, any case
    assert items == [{"name": "tabata", "work": 30, "rest": 5, "rounds": 6}]
    assert add_preset(items, "", 20, 10, 8) == items  # blank name rejected
    assert add_preset(items, "Zero", 0, 10, 8) == items  # work must be >= 1
    assert len(add_preset(items, "Other", 20, 0, 1)) == 2


def test_delete_and_describe():
    items = add_preset(add_preset([], "A", 40, 20, 5), "B", 75, 0, 3)
    assert [p["name"] for p in delete_preset(items, "A")] == ["B"]
    assert describe(items[1]) == "01:15 / 00:00 x 3"
