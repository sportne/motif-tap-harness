from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Iterable

from motiftap.events import RawEvent


# Xnee/cnee human output varies by version and options. These patterns are
# deliberately permissive starter rules. The normalized JSONL format is the
# stable boundary for the rest of the project.
_TIME_PATTERNS = [
    re.compile(r"(?:time|t)\s*[=:]\s*(?P<t>\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"^\s*(?P<t>\d+(?:\.\d+)?)\s+"),
]

_BUTTON_PATTERNS = [
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
        r"(?P<phase>KeyPress|KeyRelease|key\s+press|key\s+release).*?"
        r"(?:key|keysym|name)\s*[=: ]\s*(?P<key>[A-Za-z0-9_+\-./]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<phase>press|release).*?key\s+(?P<key>[A-Za-z0-9_+\-./]+)",
        re.IGNORECASE,
    ),
]


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


def normalize_xnee_human_lines(lines: Iterable[str]) -> list[RawEvent]:
    """Normalize a cnee human-printout stream to RawEvent objects.

    This parser is intentionally a best-effort starter. On your first real
    application, run `motif-normalize-xnee --stats` and adjust the regexes if
    your local cnee output differs.
    """

    events: list[RawEvent] = []
    fallback_t = 0.0

    for line in lines:
        text = line.strip()
        if not text:
            continue

        t = _extract_time(text, fallback_t)
        fallback_t = max(fallback_t + 0.001, t + 0.001)

        matched = False
        for pattern in _BUTTON_PATTERNS:
            match = pattern.search(text)
            if match:
                events.append(
                    RawEvent(
                        t=t,
                        kind="button",
                        phase=_normal_phase(match.group("phase")),
                        button=int(match.group("button")),
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
