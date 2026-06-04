from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


class RecordingValidationError(RuntimeError):
    """Raised when a recording command did not produce usable outputs."""


def _split_app_args(raw: list[str]) -> list[str]:
    if raw and raw[0] == "--":
        return raw[1:]
    return raw


def _require_nonempty_file(path: Path, *, hint: str) -> None:
    if not path.exists():
        raise RecordingValidationError(f"Required recording output is missing: {path}. {hint}")
    if path.stat().st_size <= 0:
        raise RecordingValidationError(f"Required recording output is empty: {path}. {hint}")


def _validate_outputs(
    *,
    meta_file: Path,
    state_file: Path,
    widget_log: Path,
    xnee_human: Path,
    used_cnee: bool,
) -> None:
    _require_nonempty_file(meta_file, hint="The recorder could not write metadata.")
    _require_nonempty_file(
        state_file,
        hint="The Xt hook did not write live state; check LD_PRELOAD and MOTIF_TAP_STATE.",
    )
    _require_nonempty_file(
        widget_log,
        hint="The Xt hook did not write snapshots; check LD_PRELOAD and MOTIF_TAP_LOG.",
    )
    if used_cnee:
        _require_nonempty_file(
            xnee_human,
            hint="cnee produced no human-readable events; check xnee.log and X11 input permissions.",
        )


def _unexpected_exit(
    *,
    name: str,
    argv: list[str],
    returncode: int | None,
    allow_signal: bool = False,
) -> str | None:
    if returncode is None or returncode == 0:
        return None
    if allow_signal and returncode < 0:
        return None
    command = " ".join(argv)
    return f"{name} exited with status {returncode}: {command}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record a Motif/Xt workflow with cnee while the Xt tap hook logs widget snapshots."
    )
    parser.add_argument("--name", required=True, help="Recording name, e.g. open_valid_file")
    parser.add_argument(
        "--output-dir", default="recordings", help="Parent directory for recordings"
    )
    parser.add_argument("--tap-so", default="./c/libxttap.so", help="Path to libxttap.so")
    parser.add_argument("--cnee", default="cnee", help="cnee executable")
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="Record for this many seconds instead of waiting for Enter",
    )
    parser.add_argument(
        "--no-cnee",
        action="store_true",
        help="Launch the app and hook only; useful for hook debugging",
    )
    parser.add_argument(
        "--app", nargs=argparse.REMAINDER, required=True, help="Application command after --"
    )
    args = parser.parse_args(argv)

    app_argv = _split_app_args(args.app)
    if not app_argv:
        parser.error("--app must be followed by the application command")

    out_dir = Path(args.output_dir) / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    state_file = out_dir / "latest-state.json"
    widget_log = out_dir / "widgets.jsonl"
    xnee_human = out_dir / "xnee-human.txt"
    xnee_log = out_dir / "xnee.log"
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
    cnee_cmd: list[str] = []
    app_exited_before_cleanup = False
    xnee_exited_before_cleanup = False
    xnee_cleanup_sent = False

    if not args.no_cnee:
        if shutil.which(args.cnee) is None:
            app.terminate()
            raise SystemExit(f"cnee executable not found: {args.cnee}")

        # cnee flags vary slightly by version. This command records mouse and
        # keyboard input as human-readable output for normalization.
        cnee_cmd = [
            args.cnee,
            "--record",
            "--mouse",
            "--keyboard",
            "--human-printout",
            "--out-file",
            str(xnee_human),
            "--err-file",
            str(xnee_log),
            "--verbose",
        ]
        if args.seconds is not None:
            cnee_cmd.extend(["--seconds-to-record", str(max(1, int(args.seconds)))])
        xnee = subprocess.Popen(cnee_cmd)

    print(f"Recording: {args.name}")
    print(f"Output:    {out_dir}")
    if args.seconds is None:
        print("Perform the workflow in the application, then press Enter here to stop.")
    else:
        print(f"Recording will stop automatically after {args.seconds:.2f} seconds.")

    try:
        if args.seconds is None:
            input()
        else:
            if xnee is not None:
                xnee.wait(timeout=args.seconds + 5)
            else:
                time.sleep(args.seconds)
    finally:
        app_exited_before_cleanup = app.poll() is not None
        xnee_exited_before_cleanup = xnee.poll() is not None if xnee else False

        if xnee and xnee.poll() is None:
            xnee_cleanup_sent = True
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

    failures = []
    app_exit = _unexpected_exit(
        name="application",
        argv=app_argv,
        returncode=app.returncode if app_exited_before_cleanup else None,
    )
    if app_exit:
        failures.append(app_exit)

    if xnee is not None:
        xnee_exit = _unexpected_exit(
            name="cnee",
            argv=cnee_cmd,
            returncode=xnee.returncode if xnee_exited_before_cleanup or xnee_cleanup_sent else None,
            allow_signal=xnee_cleanup_sent,
        )
        if xnee_exit:
            failures.append(f"{xnee_exit}; inspect {xnee_log}")

    try:
        _validate_outputs(
            meta_file=meta_file,
            state_file=state_file,
            widget_log=widget_log,
            xnee_human=xnee_human,
            used_cnee=not args.no_cnee,
        )
    except RecordingValidationError as exc:
        failures.append(str(exc))

    if failures:
        raise SystemExit("Recording failed validation:\n- " + "\n- ".join(failures))

    print(f"Saved recording in {out_dir}")
    print(
        "Next: motif-normalize-xnee {}/xnee-human.txt --out {}/events.jsonl".format(
            out_dir, out_dir
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
