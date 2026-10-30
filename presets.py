"""Saved Work/Rest profiles, stored as a JSON list."""
import json
from pathlib import Path

MAX_NAME = 24
DEFAULT_PRESETS = [
    {"name": "Tabata", "work": 20, "rest": 10, "rounds": 8},
    {"name": "Circuit", "work": 40, "rest": 20, "rounds": 5},
]


def _clean(item):
    """Return a validated preset dict, or None if the entry is unusable."""
    try:
        name = str(item["name"]).strip()[:MAX_NAME]
        work, rest, rounds = int(item["work"]), int(item["rest"]), int(item["rounds"])
    except (KeyError, TypeError, ValueError):
        return None
    if not name or work < 1 or rest < 0 or rounds < 1:
        return None
    return {"name": name, "work": work, "rest": rest, "rounds": rounds}


def load_presets(path) -> list:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return [dict(p) for p in DEFAULT_PRESETS]  # first run
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    return [p for p in map(_clean, data) if p]


def save_presets(path, presets) -> None:
    try:
        Path(path).write_text(json.dumps(presets), encoding="utf-8")
    except OSError:
        pass


def add_preset(presets, name, work, rest, rounds) -> list:
    """Return a new list with the preset added; a same name (any case) is replaced in place."""
    new = _clean({"name": name, "work": work, "rest": rest, "rounds": rounds})
    if new is None:
        return list(presets)
    result = list(presets)
    for i, p in enumerate(result):
        if p["name"].lower() == new["name"].lower():
            result[i] = new
            return result
    result.append(new)
    return result


def delete_preset(presets, name) -> list:
    return [p for p in presets if p["name"] != name]


def describe(preset) -> str:
    def mmss(s):
        return f"{s // 60:02d}:{s % 60:02d}"
    return f"{mmss(preset['work'])} / {mmss(preset['rest'])} x {preset['rounds']}"
