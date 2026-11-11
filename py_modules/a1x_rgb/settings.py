"""Load and save the plugin's settings file."""

from __future__ import annotations

import json
import os


def load(path: str) -> dict:
    """Return the saved settings dict, or {} if missing or unreadable."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path: str, settings: dict) -> None:
    """Write settings atomically (temp file + rename)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
