from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time


def _split_app_args(raw: list[str]) -> list[str]:
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record a Motif/Xt workflow with cnee while the Xt tap hook logs widget snapshots."
    )
    parser.add_argument("--name", required=True, help="Recording name, e.g. open_valid_file")
    parser.add_argument("--output-dir", default="recordings", help="Parent directory for recordings")
    parser.add_argument("--tap-so", default="./c/libxttap.so", help="Path to libxttap.so")
    parser.add_argument("--cnee", default="cnee", help="cnee executable")
    parser.add_argument("--no-cnee", action="store_true", help="Launch the app and hook only; useful for hook debugging")
    parser.add_argument("--app", nargs=argparse.REMAINDER, required=True, help="Application command after --")
    args = parser.parse_args(argv)

    app_argv = _split_app_args(args.app)
    if not app_argv:
        parser.error("--app must be followed by the application command")

    out_dir = Path(args.output_dir) / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    state_file = out_dir / "latest-state.json"
    widget_log = out_dir / "widgets.jsonl"
    xnee_file = out_dir / "xnee.xns"
    xnee_human = out_dir / "xnee-human.txt"
    meta_file = out_dir / "meta.json"

    env = os.environ.copy()
    env["MOTIF_TAP_STATE"] = str(state_file)
    env["MOTIF_TAP_LOG"] = str(widget_log)

    existing_preload = env.get("LD_PRELOAD", "")
    env["LD_PRELOAD"] = f"{args.tap_so}:{existing_preload}" if existing_preload else args.tap_so

    record_start = time.monotonic()
    meta_file.write_text(
        json.dumps(
            {
                "record_start_monotonic": record_start,
                "app": app_argv,
                "created_unix_time": time.time(),
                "tap_so": args.tap_so,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    app = subprocess.Popen(app_argv, env=env)
    xnee: subprocess.Popen[bytes] | None = None

    if not args.no_cnee:
        if shutil.which(args.cnee) is None:
            app.terminate()
            raise SystemExit(f"cnee executable not found: {args.cnee}")

        # cnee flags vary slightly by version. This is a starter command that
        # records mouse+keyboard input and requests human output for normalization.
        xnee = subprocess.Popen(
            [
                args.cnee,
                "--record",
                "--mouse",
                "--keyboard",
                "--human-printout",
                "--out-file",
                str(xnee_file),
                "--err-file",
                str(xnee_human),
                "--verbose",
            ]
        )

    print(f"Recording: {args.name}")
    print(f"Output:    {out_dir}")
    print("Perform the workflow in the application, then press Enter here to stop.")

    try:
        input()
    finally:
        if xnee and xnee.poll() is None:
            xnee.send_signal(signal.SIGINT)
            try:
                xnee.wait(timeout=3)
            except subprocess.TimeoutExpired:
                xnee.terminate()

        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=3)
            except subprocess.TimeoutExpired:
                app.kill()

    print(f"Saved recording in {out_dir}")
    print("Next: motif-normalize-xnee {}/xnee-human.txt --out {}/events.jsonl".format(out_dir, out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
