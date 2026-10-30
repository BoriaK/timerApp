"""Persistent user settings stored as a small JSON file."""
import json
from pathlib import Path

DEFAULTS = {"background": True}


def load_settings(path) -> dict:
    settings = dict(DEFAULTS)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key in DEFAULTS:
            if isinstance(data.get(key), type(DEFAULTS[key])):
                settings[key] = data[key]
    except (OSError, ValueError, AttributeError):
        pass  # missing or corrupt file -> defaults
    return settings


def save_settings(path, settings: dict) -> None:
    try:
        Path(path).write_text(json.dumps(settings), encoding="utf-8")
    except OSError:
        pass
