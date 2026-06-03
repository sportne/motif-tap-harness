from __future__ import annotations

import argparse
from pathlib import Path

from motiftap.widget_map import WidgetTimeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print widgets from a Motif Tap latest-state.json file.")
    parser.add_argument("state_file")
    parser.add_argument("--contains", default=None, help="Only show paths containing this substring")
    args = parser.parse_args(argv)

    timeline = WidgetTimeline.from_state_file(args.state_file)
    snapshot = timeline.snapshots[-1]

    rows = []
    for widget in snapshot.widgets:
        if args.contains and args.contains not in widget.path:
            continue
        rows.append(widget)

    if not rows:
        print("No widgets matched.")
        return 0

    path_width = min(max(len(w.path) for w in rows), 90)
    print(f"{'PATH':{path_width}}  {'CLASS':22s}  {'GEOMETRY':18s}  FLAGS")
    print("-" * (path_width + 2 + 22 + 2 + 18 + 2 + 10))
    for w in rows:
        flags = []
        if w.managed:
            flags.append("managed")
        if w.sensitive:
            flags.append("sensitive")
        if w.realized:
            flags.append("realized")
        geometry = f"{w.root_x},{w.root_y} {w.width}x{w.height}"
        print(f"{w.path[:path_width]:{path_width}}  {w.klass[:22]:22s}  {geometry:18s}  {','.join(flags)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
