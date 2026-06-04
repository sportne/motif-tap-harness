# CI guide

Motif GUI tests need a predictable X11 environment.

---

## Fast checks versus live-loop proof

The default fast checks should stay small and deterministic:

```bash
make doctor
make check
```

`make doctor` verifies the local development prerequisites and reports optional
GUI/live-loop tools separately from required fast-check dependencies.

`make check` runs:

```bash
make lint
make format-check
make test
make -C c
```

The live-loop proof is intentionally slower. It starts Xvfb and `openbox`,
records a real Motif calculator workflow with `cnee`, translates it, replays the
generated pytest through `MotifApp`, and asserts the calculator result.

Docker:

```bash
docker build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
docker run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

Podman:

```bash
podman build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
podman run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

The `--rm` form is good for a quick pass/fail run. To inspect artifacts after
the container exits, bind mount an artifact directory:

```bash
mkdir -p live-loop-artifacts
docker run --rm \
  -e MOTIF_TAP_LIVE_ARTIFACT_DIR=/artifacts \
  -v "$PWD/live-loop-artifacts:/artifacts" \
  motif-tap-live-loop scripts/live-loop-demo.sh
```

Use the same pattern with `podman run --rm`.

The demo writes runtime artifacts under `MOTIF_TAP_LIVE_ARTIFACT_DIR`, which
defaults to `/tmp/motif-tap-live-loop` inside the container:

```text
translate.log
motif-record.log
normalize.log
xvfb.log
openbox.log
clicks.env
recordings/calculator_multiply/
  meta.json
  latest-state.json
  widgets.jsonl
  xnee-human.txt
  events.jsonl
  xnee.log
hook-smoke/
  latest-state.json
  widgets.jsonl
  inspect-state.txt
  xvfb.log
  openbox.log
  calculator.log
replay/
  pytest.log
  xvfb-replay.log
  openbox-replay.log
```

Generated replay diagnostics from `MotifApp(keep_artifacts=True)` are written to
a `motif-test-*` directory inside the container on failure. When preserving
artifacts, set `MOTIF_TAP_LIVE_ARTIFACT_DIR` to a mounted directory and copy any
reported `motif-test-*` path before the container exits if deeper inspection is
needed.

---

## Minimal CI command

```bash
xvfb-run -a pytest tests/gui
```

This is enough for simple applications that do not depend heavily on window-manager behavior.

---

## CI with a window manager

Some Motif applications expect focus, window decorations, transient dialogs, or specific window manager behavior.

A generic pattern:

```bash
Xvfb :99 -screen 0 1280x1024x24 &
export DISPLAY=:99
sleep 1

# Optional. Pick a lightweight manager available on your system.
openbox &
sleep 1

pytest tests/gui
```

---

## Environment stability checklist

Pin or control:

```text
screen size
color depth
fonts
locale
Motif app-defaults/resource files
home directory / preferences
working directory
test data directory
window manager
network dependencies
clock/timezone if displayed by the app
```

---

## Artifact collection

On failure, collect:

```text
motif-test-* session directory
latest-state.json
widgets.jsonl
xwininfo-tree.txt
visible-windows.txt
screen.xwd
application stdout/stderr
application logs
test input data
```

The starter harness writes diagnostics into the temporary session directory. Set `keep_artifacts=True` while debugging locally:

```python
with MotifApp(["./my_app"], keep_artifacts=True) as app:
    ...
```

For CI, adapt the harness or pytest configuration to copy the session directory into your CI artifact directory.

---

## Recommended test grouping

Separate fast GUI smoke tests from longer workflows:

```text
tests/gui/smoke/
tests/gui/workflows/
tests/gui/visual/
```

Run smoke tests on every change. Run longer workflows nightly or before releases.

---

## Flake control

Avoid fixed sleeps as the primary synchronization mechanism.

Prefer:

```python
app.wait_for_widget("myApp.completeDialog.okButton")
app.wait_for_window("Complete")
assert Path("/tmp/output.dat").exists()
```

Use tiny sleeps only as debounce after a real condition has been met.

---

## Exit cleanup

Legacy GUI apps sometimes leave child processes, lock files, or user preferences behind.

Your CI wrapper should:

```text
use a temporary HOME
use a temporary working directory
clean test output directories
kill leftover app processes after test completion
archive logs before cleanup
```

---

## Suggested pytest marker

Add a marker in your own `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
  "gui: tests requiring X11 and the Motif application",
]
```

Then:

```bash
pytest -m gui
```

---

## Live-loop troubleshooting

If the container image does not build, confirm the base image can install:

```text
libmotif-dev
libxt-dev
libx11-dev
xvfb
openbox
xdotool
xnee
gcc
make
python3-venv
```

If Xvfb does not start, inspect Xvfb logs under the artifact directory:

```text
xvfb.log
hook-smoke/xvfb.log
replay/xvfb-replay.log
```

The scripts try displays `:99` through `:109` without deleting existing lock
files.

If `cnee` records zero events, inspect:

```text
/tmp/motif-tap-live-loop/recordings/calculator_multiply/xnee-human.txt
/tmp/motif-tap-live-loop/recordings/calculator_multiply/xnee.log
```

The normalizer expects `Event=ButtonPress` and `Event=ButtonRelease` lines with
`rootX` and `rootY` fields for the container's `cnee` output.

If hook state is missing widgets, run:

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-hook-smoke.sh
```

That script prints the observed widget tree and fails if calculator button paths
are missing.

If replay clicks the wrong target, compare the recorded `events.jsonl` root
coordinates with the matching widget geometry in `widgets.jsonl`. The calculator
workflow should translate to four `HIGH` confidence widget-path clicks.

If replay timing is flaky, inspect `replay/pytest.log` and any reported
`motif-test-*/failure` diagnostics. Typical symptoms are clicks before a widget
is realized, stale state in `latest-state.json`, or result-file assertions
running before the application has written the value. Prefer widening
condition-based waits or the `MotifApp` timeout over adding fixed sleeps.
