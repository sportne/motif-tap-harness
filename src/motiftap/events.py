from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawEvent:
    """Normalized raw input event.

    Times are seconds relative to the start of recording unless the caller has
    already shifted them to the Xt hook's monotonic clock.
    """

    t: float
    kind: str
    phase: str | None = None
    key: str | None = None
    button: int | None = None
    x: int | None = None
    y: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawEvent":
        return cls(
            t=float(data["t"]),
            kind=str(data["kind"]),
            phase=data.get("phase"),
            key=data.get("key"),
            button=int(data["button"]) if data.get("button") is not None else None,
            x=int(data["x"]) if data.get("x") is not None else None,
            y=int(data["y"]) if data.get("y") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"t": self.t, "kind": self.kind}
        if self.phase is not None:
            out["phase"] = self.phase
        if self.key is not None:
            out["key"] = self.key
        if self.button is not None:
            out["button"] = self.button
        if self.x is not None:
            out["x"] = self.x
        if self.y is not None:
            out["y"] = self.y
        return out


@dataclass(frozen=True)
class Action:
    """Higher-level action generated from raw events."""

    t: float
    op: str
    data: dict[str, object]


def read_normalized_events(
    path: str | Path,
    *,
    session_start_monotonic: float = 0.0,
) -> list[RawEvent]:
    events: list[RawEvent] = []
    p = Path(path)

    with p.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                event = RawEvent.from_dict(json.loads(line))
            except Exception as exc:
                raise ValueError(f"Invalid event on {p}:{line_number}: {exc}") from exc

            events.append(
                RawEvent(
                    t=session_start_monotonic + event.t,
                    kind=event.kind,
                    phase=event.phase,
                    key=event.key,
                    button=event.button,
                    x=event.x,
                    y=event.y,
                )
            )

    return events


def write_normalized_events(events: list[RawEvent], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event.to_dict(), sort_keys=True))
            f.write("\n")


def _looks_like_printable_key(key: str) -> bool:
    if len(key) == 1:
        return True
    return key in {"space", "slash", "period", "comma", "minus", "underscore"}


def _key_to_text(key: str) -> str:
    mapping = {
        "space": " ",
        "slash": "/",
        "period": ".",
        "comma": ",",
        "minus": "-",
        "underscore": "_",
    }
    return mapping.get(key, key)


def coalesce_events(
    events: list[RawEvent],
    *,
    click_max_seconds: float = 0.75,
    click_max_pixels: float = 5.0,
    text_gap_seconds: float = 0.35,
) -> list[Action]:
    """Convert raw events into a small set of replay actions.

    - Button press/release pairs become ``click`` actions.
    - Printable key streams become ``type_text`` actions.
    - Non-printable key presses become ``press`` actions.
    """

    actions: list[Action] = []
    pending_button: dict[int, RawEvent] = {}
    text_buffer: list[str] = []
    text_start_t: float | None = None
    text_last_t: float | None = None

    def flush_text() -> None:
        nonlocal text_buffer, text_start_t, text_last_t
        if text_buffer:
            actions.append(
                Action(
                    t=text_start_t if text_start_t is not None else 0.0,
                    op="type_text",
                    data={"text": "".join(text_buffer)},
                )
            )
        text_buffer = []
        text_start_t = None
        text_last_t = None

    for event in sorted(events, key=lambda e: e.t):
        if event.kind == "button" and event.button is not None:
            flush_text()
            if event.phase == "press":
                pending_button[event.button] = event
                continue

            if event.phase == "release":
                press = pending_button.pop(event.button, None)
                if press and press.x is not None and press.y is not None:
                    release_x = event.x if event.x is not None else press.x
                    release_y = event.y if event.y is not None else press.y
                    dx = release_x - press.x
                    dy = release_y - press.y
                    dt = event.t - press.t

                    if dt <= click_max_seconds and math.hypot(dx, dy) <= click_max_pixels:
                        actions.append(
                            Action(
                                t=press.t,
                                op="click",
                                data={"button": event.button, "x": press.x, "y": press.y},
                            )
                        )
                    else:
                        actions.append(
                            Action(
                                t=press.t,
                                op="drag_or_raw_mouse",
                                data={
                                    "button": event.button,
                                    "x1": press.x,
                                    "y1": press.y,
                                    "x2": release_x,
                                    "y2": release_y,
                                },
                            )
                        )
                continue

        if event.kind == "key" and event.phase == "press" and event.key:
            key = event.key
            if _looks_like_printable_key(key):
                if text_last_t is not None and event.t - text_last_t > text_gap_seconds:
                    flush_text()
                if text_start_t is None:
                    text_start_t = event.t
                text_last_t = event.t
                text_buffer.append(_key_to_text(key))
            else:
                flush_text()
                actions.append(Action(t=event.t, op="press", data={"key": key}))

    flush_text()
    return actions
