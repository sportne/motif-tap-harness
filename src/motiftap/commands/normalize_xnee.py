from __future__ import annotations

import argparse

from motiftap.events import write_normalized_events
from motiftap.xnee_normalize import normalize_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize cnee/Xnee output to Motif Tap JSONL events."
    )
    parser.add_argument("input", help="Input cnee human output or already-normalized JSONL")
    parser.add_argument("--out", required=True, help="Output events.jsonl")
    parser.add_argument("--input-format", choices=["auto", "jsonl", "xnee-human"], default="auto")
    parser.add_argument("--stats", action="store_true", help="Print event counts")
    args = parser.parse_args(argv)

    events = normalize_file(args.input, input_format=args.input_format)
    write_normalized_events(events, args.out)

    if args.stats:
        button = sum(1 for e in events if e.kind == "button")
        key = sum(1 for e in events if e.kind == "key")
        print(f"events={len(events)} button={button} key={key}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
