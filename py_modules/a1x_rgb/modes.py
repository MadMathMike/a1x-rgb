"""Device-agnostic description of lighting modes, and settings validation.

A device describes what it supports with a plain dict (JSON-serialisable, so
the frontend can render controls straight from it):

    {
      "default_mode": "solid",
      "modes": [
        {"key": "off", "label": "Off", "controls": []},
        {"key": "solid", "label": "Solid", "controls": ["hue", ...]},
      ],
      "controls": {
        "hue": {"type": "slider", "label": "Hue", "min": 0, "max": 360,
                "step": 5, "unit": "°", "default": 30},
        "level": {"type": "choice", "label": "Brightness",
                  "options": [{"key": "low", "label": "Low"}, ...],
                  "default": "medium"},
      },
    }

Settings are a flat dict: {"mode": ..., <control key>: value, ...}. Values
for every control are kept, even ones the current mode doesn't use, so
switching modes keeps the user's earlier choices.
"""

from __future__ import annotations

from typing import Any


def slider(label: str, lo: int, hi: int, step: int, default: int, unit: str = "") -> dict:
    return {
        "type": "slider",
        "label": label,
        "min": lo,
        "max": hi,
        "step": step,
        "unit": unit,
        "default": default,
    }


def choice(label: str, options: list[tuple[str, str]], default: str) -> dict:
    return {
        "type": "choice",
        "label": label,
        "options": [{"key": k, "label": v} for k, v in options],
        "default": default,
    }


def defaults(desc: dict) -> dict:
    out: dict[str, Any] = {"mode": desc["default_mode"]}
    for key, ctrl in desc["controls"].items():
        out[key] = ctrl["default"]
    return out


def _check_control(key: str, ctrl: dict, value: Any) -> Any:
    """Return the validated value, or raise ValueError."""
    if ctrl["type"] == "slider":
        # bool is an int subclass; reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key}: expected a number, got {value!r}")
        return int(min(max(round(value), ctrl["min"]), ctrl["max"]))
    if ctrl["type"] == "choice":
        if value not in {o["key"] for o in ctrl["options"]}:
            raise ValueError(f"{key}: invalid option {value!r}")
        return value
    raise ValueError(f"{key}: unknown control type {ctrl['type']!r}")


def normalize(desc: dict, settings: dict, strict: bool = False) -> dict:
    """Validate settings against a description and fill in missing values.

    Unknown keys are dropped and slider values are rounded and clamped to
    their range. Invalid values raise ValueError when `strict` (input from
    the UI). Otherwise they quietly fall back to the default (loading a
    possibly stale settings file).
    """
    out = defaults(desc)

    mode = settings.get("mode", out["mode"])
    if mode in {m["key"] for m in desc["modes"]}:
        out["mode"] = mode
    elif strict:
        raise ValueError(f"mode: invalid option {mode!r}")

    for key, ctrl in desc["controls"].items():
        if key not in settings:
            continue
        try:
            out[key] = _check_control(key, ctrl, settings[key])
        except ValueError:
            if strict:
                raise
    return out
