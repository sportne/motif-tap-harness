from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Widget:
    """A single widget in an Xt snapshot."""

    path: str
    name: str
    klass: str
    root_x: int
    root_y: int
    width: int
    height: int
    depth: int
    window: str | None = None
    managed: bool = True
    sensitive: bool = True
    realized: bool = True

    def contains(self, x: int, y: int) -> bool:
        return (
            self.root_x <= x < self.root_x + self.width
            and self.root_y <= y < self.root_y + self.height
        )

    @property
    def area(self) -> int:
        return self.width * self.height

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Widget":
        return cls(
            path=str(data["path"]),
            name=str(data.get("name", "")),
            klass=str(data.get("class", data.get("klass", ""))),
            window=data.get("window"),
            root_x=int(data.get("root_x", 0)),
            root_y=int(data.get("root_y", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            depth=int(data.get("depth", str(data["path"]).count("."))),
            managed=bool(data.get("managed", True)),
            sensitive=bool(data.get("sensitive", True)),
            realized=bool(data.get("realized", True)),
        )


@dataclass(frozen=True)
class Snapshot:
    """A point-in-time Xt widget tree."""

    t: float
    widgets: list[Widget]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            t=float(data["t"]),
            widgets=[Widget.from_dict(w) for w in data.get("widgets", [])],
        )


class WidgetTimeline:
    """Time-indexed widget snapshots.

    The translator uses this to answer questions such as:

        At time 123.456, which widget contained root coordinate (842, 416)?
    """

    def __init__(self, snapshots: list[Snapshot]):
        if not snapshots:
            raise ValueError("WidgetTimeline requires at least one snapshot")
        self.snapshots = sorted(snapshots, key=lambda s: s.t)
        self.times = [s.t for s in self.snapshots]

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "WidgetTimeline":
        snapshots: list[Snapshot] = []
        p = Path(path)

        with p.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on {p}:{line_number}: {exc}") from exc

                if record.get("type") == "snapshot":
                    snapshots.append(Snapshot.from_dict(record))

        return cls(snapshots)

    @classmethod
    def from_state_file(cls, path: str | Path) -> "WidgetTimeline":
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        if record.get("type") != "snapshot":
            raise ValueError(f"State file {path} is not a snapshot record")
        return cls([Snapshot.from_dict(record)])

    def snapshot_at(self, t: float) -> Snapshot:
        index = bisect_right(self.times, t) - 1
        if index < 0:
            index = 0
        return self.snapshots[index]

    def hit_test(self, t: float, x: int, y: int) -> Widget | None:
        """Return the deepest managed/sensitive widget containing a coordinate."""

        snapshot = self.snapshot_at(t)
        candidates = [
            widget
            for widget in snapshot.widgets
            if widget.managed
            and widget.sensitive
            and widget.realized
            and widget.width > 0
            and widget.height > 0
            and widget.contains(x, y)
        ]

        if not candidates:
            return None

        # Prefer the deepest widget. If depths tie, prefer the smallest area.
        return max(candidates, key=lambda w: (w.depth, -w.area))

    def find_path(self, path: str, *, t: float | None = None) -> Widget | None:
        snapshot = self.snapshots[-1] if t is None else self.snapshot_at(t)
        for widget in snapshot.widgets:
            if widget.path == path:
                return widget
        return None

    def paths(self) -> list[str]:
        return [widget.path for widget in self.snapshots[-1].widgets]
