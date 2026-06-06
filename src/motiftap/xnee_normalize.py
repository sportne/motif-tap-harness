from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from motiftap.events import RawEvent

# Xnee/cnee human output varies by version and options. These patterns are
# deliberately permissive starter rules. The normalized JSONL format is the
# stable boundary for the rest of the project.
_TIME_PATTERNS = [
    re.compile(r"\b(?:time|t)\b\s*[=:]\s*(?P<t>\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"^\s*(?P<t>\d+(?:\.\d+)?)\s+"),
]

_BUTTON_PATTERNS = [
    re.compile(
        r"Event=(?P<phase>ButtonPress|ButtonRelease).*?"
        r"rootX=(?P<x>-?\d+)\s+rootY=(?P<y>-?\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<phase>ButtonPress|ButtonRelease|button\s+press|button\s+release).*?"
        r"(?:button|btn)\s*[=: ]\s*(?P<button>\d+).*?"
        r"x\s*[=: ]\s*(?P<x>-?\d+).*?y\s*[=: ]\s*(?P<y>-?\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<phase>press|release).*?button\s+(?P<button>\d+).*?"
        r"\((?P<x>-?\d+)\s*,\s*(?P<y>-?\d+)\)",
        re.IGNORECASE,
    ),
]

_KEY_PATTERNS = [
    re.compile(
        r"(?P<phase>KeyPress|KeyRelease).*?"
        r"(?:keysym|keyname)\s*[=: ]\s*(?:0x[0-9a-fA-F]+\s*)?"
        r"(?P<key>[A-Za-z0-9_+\-./]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<phase>KeyPress|KeyRelease|key\s+press|key\s+release).*?"
        r"(?:key|keysym|name)\s*[=: ]\s*(?P<key>[A-Za-z0-9_+\-./]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<phase>press|release).*?key\s+(?P<key>[A-Za-z0-9_+\-./]+)",
        re.IGNORECASE,
    ),
]

_XTEST_KEYCODE_PATTERN = re.compile(
    r"Event=\s*not defined\s+Number=\d+,(?P<number>[23]),\d+,\d+,\d+,"
    r"(?P<keycode>\d+),.*?(?:XTEST keyboard|Virtual core keyboard)",
    re.IGNORECASE,
)

_KEY_EVENT_PATTERN = re.compile(r"Event=(?P<phase>KeyPress|KeyRelease)\b", re.IGNORECASE)
_STATE_PATTERN = re.compile(r"\bstate=(?P<state>\d+)\b")

_KEYCODE_NAMES = {
    9: "Escape",
    10: "1",
    11: "2",
    12: "3",
    13: "4",
    14: "5",
    15: "6",
    16: "7",
    17: "8",
    18: "9",
    19: "0",
    20: "minus",
    21: "equal",
    22: "BackSpace",
    23: "Tab",
    24: "q",
    25: "w",
    26: "e",
    27: "r",
    28: "t",
    29: "y",
    30: "u",
    31: "i",
    32: "o",
    33: "p",
    36: "Return",
    38: "a",
    39: "s",
    40: "d",
    41: "f",
    42: "g",
    43: "h",
    44: "j",
    45: "k",
    46: "l",
    50: "Shift_L",
    52: "z",
    53: "x",
    54: "c",
    55: "v",
    56: "b",
    57: "n",
    58: "m",
    62: "Shift_R",
    65: "space",
    75: "F9",
}

_SHIFTED_KEYCODE_NAMES = {
    10: "exclam",
    11: "at",
    12: "numbersign",
    13: "dollar",
    14: "percent",
    15: "asciicircum",
    16: "ampersand",
    17: "asterisk",
    18: "parenleft",
    19: "parenright",
    20: "underscore",
    21: "plus",
}

_IGNORED_XTEST_KEYS = {"Shift_L", "Shift_R"}


def _extract_time(line: str, fallback: float) -> float:
    for pattern in _TIME_PATTERNS:
        match = pattern.search(line)
        if match:
            return float(match.group("t"))
    return fallback


def _normal_phase(phase: str) -> str:
    p = phase.lower().replace(" ", "")
    if "release" in p:
        return "release"
    return "press"


def _state_value(line: str) -> int:
    match = _STATE_PATTERN.search(line)
    if not match:
        return 0
    return int(match.group("state"))


def _xnee_key_name(keycode: int, state: int, pressed_keys: dict[int, str]) -> str | None:
    if state & 1 and keycode in _SHIFTED_KEYCODE_NAMES:
        return _SHIFTED_KEYCODE_NAMES[keycode]
    if keycode in pressed_keys:
        return pressed_keys[keycode]
    key = _KEYCODE_NAMES.get(keycode)
    if state & 1 and key and len(key) == 1 and key.isalpha():
        return key.upper()
    return key


def normalize_xnee_human_lines(lines: Iterable[str]) -> list[RawEvent]:
    """Normalize a cnee human-printout stream to RawEvent objects.

    This parser is intentionally a best-effort starter. On your first real
    application, run `motif-normalize-xnee --stats` and adjust the regexes if
    your local cnee output differs.
    """

    events: list[RawEvent] = []
    fallback_t = 0.0
    pending_xnee_key: tuple[float, int, str] | None = None
    pressed_xnee_keys: dict[int, str] = {}

    for line in lines:
        text = line.strip()
        if not text:
            continue

        t = _extract_time(text, fallback_t)
        fallback_t = max(fallback_t + 0.001, t + 0.001)

        xnee_key_match = _XTEST_KEYCODE_PATTERN.search(text)
        if xnee_key_match:
            phase = "press" if xnee_key_match.group("number") == "2" else "release"
            pending_xnee_key = (t, int(xnee_key_match.group("keycode")), phase)
            continue

        key_event_match = _KEY_EVENT_PATTERN.search(text)
        if pending_xnee_key and key_event_match:
            key_t, keycode, expected_phase = pending_xnee_key
            phase = _normal_phase(key_event_match.group("phase"))
            pending_xnee_key = None
            if phase == expected_phase:
                key = _xnee_key_name(keycode, _state_value(text), pressed_xnee_keys)
                if key is not None:
                    if phase == "press":
                        pressed_xnee_keys[keycode] = key
                    else:
                        pressed_xnee_keys.pop(keycode, None)
                    if key not in _IGNORED_XTEST_KEYS:
                        events.append(RawEvent(t=key_t, kind="key", phase=phase, key=key))
                    continue

        matched = False
        for pattern in _BUTTON_PATTERNS:
            match = pattern.search(text)
            if match:
                events.append(
                    RawEvent(
                        t=t,
                        kind="button",
                        phase=_normal_phase(match.group("phase")),
                        button=int(match.groupdict().get("button") or 1),
                        x=int(match.group("x")),
                        y=int(match.group("y")),
                    )
                )
                matched = True
                break
        if matched:
            continue

        for pattern in _KEY_PATTERNS:
            match = pattern.search(text)
            if match:
                events.append(
                    RawEvent(
                        t=t,
                        kind="key",
                        phase=_normal_phase(match.group("phase")),
                        key=match.group("key"),
                    )
                )
                matched = True
                break

    return events


def normalize_jsonl_lines(lines: Iterable[str]) -> list[RawEvent]:
    events: list[RawEvent] = []
    for line in lines:
        if line.strip():
            events.append(RawEvent.from_dict(json.loads(line)))
    return events


def normalize_file(path: str | Path, *, input_format: str = "auto") -> list[RawEvent]:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if input_format == "auto":
        first_nonempty = next((line.strip() for line in lines if line.strip()), "")
        input_format = "jsonl" if first_nonempty.startswith("{") else "xnee-human"

    if input_format == "jsonl":
        return normalize_jsonl_lines(lines)
    if input_format == "xnee-human":
        return normalize_xnee_human_lines(lines)

    raise ValueError(f"Unsupported input format: {input_format}")
