# Task: Container Replay Test

Status: Done
Type: AFK
Depends on: 0005

## Description

Run the translated calculator test inside the live-loop container and prove the
replay harness can drive a fresh calculator process through `xdotool` while
resolving live widget geometry from the Xt hook state file.

This is the primary proof that the project works in a live loop against a real
Motif application under X11.

## Allowed Changes

- `scripts/**` for the end-to-end replay script.
- `tests/gui/**` for the replay pytest.
- `containers/live-loop/**` for the container entry point or helper scripts.
- `src/motiftap/harness.py` only for defects exposed by live replay.
- `tests/**` for focused harness regression tests.

## Barred Changes

- Do not assert success by inspecting generated code only; this task must run
  the live calculator.
- Do not bypass `MotifApp` for replay.
- Do not use raw root-coordinate replay as the primary success path.
- Do not require a host X server; the proof must run under container-managed
  Xvfb.

## Acceptance Criteria

- [x] A single command starts Xvfb, runs the replay pytest, and shuts down cleanly.
- [x] The pytest launches the calculator through `MotifApp`.
- [x] The replay clicks live widget paths, not stale recording coordinates.
- [x] The test evaluates at least `7 * 6 =`.
- [x] The test asserts `/tmp/motif-calc/result.txt` contains `42`.
- [x] On failure, artifacts include `latest-state.json`, `widgets.jsonl`,
      stdout/stderr logs, window info where available, and a screen dump where
      available.

## Validation Required

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

The command must fail non-zero if recording, normalization, translation,
replay, or assertion fails.

## Notes

- This task may combine the earlier scripts into `scripts/live-loop-demo.sh`,
  but keep the smaller scripts useful for debugging.
- If the first replay is flaky, capture artifacts before changing timing or
  synchronization behavior.
