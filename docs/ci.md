# CI guide

Motif GUI tests need a predictable X11 environment.

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
