"""Remembers the timer and work/rest values used last, as a small JSON file."""
import json
from pathlib import Path


def load_last_used(path, defaults: dict) -> dict:
    values = dict(defaults)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key in defaults:
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                values[key] = value
    except (OSError, ValueError, AttributeError):
        pass  # missing or corrupt file -> defaults
    return values


def save_last_used(path, values: dict) -> None:
    try:
        Path(path).write_text(json.dumps(values), encoding="utf-8")
    except OSError:
        pass
