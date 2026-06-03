from __future__ import annotations

from pathlib import Path
import argparse

from motiftap.translator import translate_recording


def _split_app_args(raw: list[str] | None) -> list[str] | None:
    if not raw:
        return None
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Translate a Motif Tap recording into a Python pytest file.")
    parser.add_argument("recording_dir", help="Recording directory containing meta.json, events.jsonl, widgets.jsonl")
    parser.add_argument("--out", required=True, help="Output Python test file")
    parser.add_argument("--test-name", default=None, help="Test function suffix; defaults to recording directory name")
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

    print(f"Wrote {out}")
    print("Translation confidence counts:")
    for key in ["HIGH", "MEDIUM", "LOW", "TODO"]:
        print(f"  {key:6s} {result.counts.get(key, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
