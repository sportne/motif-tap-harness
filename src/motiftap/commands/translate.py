from __future__ import annotations

import argparse
from pathlib import Path

from motiftap.translator import render_report, translate_recording


def _split_app_args(raw: list[str] | None) -> list[str] | None:
    if not raw:
        return None
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Translate a Motif Tap recording into a Python pytest file."
    )
    parser.add_argument(
        "recording_dir",
        help="Recording directory containing meta.json, events.jsonl, widgets.jsonl",
    )
    parser.add_argument("--out", required=True, help="Output Python test file")
    parser.add_argument("--report", default=None, help="Optional translation report path")
    parser.add_argument(
        "--fail-on-todo",
        action="store_true",
        help="Exit nonzero if translation produced TODO actions",
    )
    parser.add_argument(
        "--test-name",
        default=None,
        help="Test function suffix; defaults to recording directory name",
    )
    parser.add_argument("--app", nargs=argparse.REMAINDER, help="Override app argv after --")
    args = parser.parse_args(argv)

    result = translate_recording(
        args.recording_dir,
        app_argv=_split_app_args(args.app),
        test_name=args.test_name,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.code, encoding="utf-8")

    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            render_report(result, title=f"Translation report: {Path(args.recording_dir).name}"),
            encoding="utf-8",
        )

    print(f"Wrote {out}")
    print("Translation confidence counts:")
    for key in ["HIGH", "MEDIUM", "LOW", "TODO"]:
        print(f"  {key:6s} {result.counts.get(key, 0)}")
    if args.report:
        print(f"Wrote report {args.report}")
    if args.fail_on_todo and result.counts.get("TODO", 0) > 0:
        raise SystemExit("Translation produced TODO actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
