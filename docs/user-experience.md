# User experience

This document describes what day-to-day use should feel like for a test author.

The intended user is someone responsible for regression testing a legacy Motif application who wants meaningful GUI coverage without rewriting the application.

---

## First-hour experience

The first useful session should look like this:

```bash
git clone <repo-url> motif-tap-harness
cd motif-tap-harness
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
make -C c
pytest
```

Then run a smoke recording:

```bash
motif-record \
  --name smoke_open_file \
  --tap-so ./c/libxttap.so \
  --app /path/to/my_motif_app --test-mode
```

The user performs the workflow manually:

```text
1. Wait for the main window.
2. Open the File menu.
3. Choose Open.
4. Enter a known test filename.
5. Click OK.
6. Wait for the success dialog.
7. Close the dialog.
```

Then they press Enter in the terminal.

Next:

```bash
motif-normalize-xnee \
  recordings/smoke_open_file/xnee-human.txt \
  --out recordings/smoke_open_file/events.jsonl \
  --stats
```

Then:

```bash
motif-translate \
  recordings/smoke_open_file \
  --out tests/test_smoke_open_file.py
```

Expected terminal output:

```text
Wrote tests/test_smoke_open_file.py
Translation confidence counts:
  HIGH   12
  MEDIUM 1
  LOW    1
  TODO   0
```

The user opens the generated test and reviews it.

---

## What the generated test should look like

A good generated test should be readable:

```python
def test_smoke_open_file():
    with MotifApp(["/path/to/my_motif_app", "--test-mode"]) as app:
        app.wait_for_idle()
        app.click("myApp.mainWindow.menuBar.fileMenu")
        app.click("myApp.fileMenu.openItem")
        app.click("myApp.openDialog.fileText")
        app.type_text("/tmp/input.dat")
        app.press("Return")
        app.wait_for_widget("myApp.completeDialog.okButton")
        app.click("myApp.completeDialog.okButton")

        assert Path("/tmp/output.dat").exists()
```

The user should not need to understand the X protocol, Xnee internals, Xt private structures, or window manager behavior to make sense of the test.

---

## Review workflow

The reviewer should scan for comments:

```python
# HIGH
# MEDIUM
# LOW
# TODO
```

The usual actions are:

### HIGH

Keep as-is.

```python
app.click("myApp.mainWindow.form.applyButton")  # HIGH: XmPushButton
```

### MEDIUM

Probably keep, but confirm it is meaningful.

```python
app.click("myApp.mainWindow.optionsPanel.someChild")  # MEDIUM
```

### LOW

Consider replacing with a better semantic action.

```python
app.click_relative("myApp.mainWindow.drawingArea", 183, 72)
```

A drawing area often represents application-specific content. The right long-term test may be:

```python
app.click_relative("myApp.mainWindow.drawingArea", 183, 72)
assert app.log_contains("selected node A17")
```

or a domain-specific helper:

```python
app.canvas_click_node("A17")
```

### TODO

Needs human attention.

```python
# TODO: drag gesture recorded; review manually
```

---

## Test author responsibilities

The automation can generate interactions, but the test author should add assertions.

Good assertions:

```python
assert Path("/tmp/output/report.dat").exists()
assert "completed successfully" in app.read_log()
app.wait_for_widget("myApp.completeDialog.okButton")
assert db.lookup_job("smoke_open_file").status == "complete"
```

Weaker assertions:

```python
app.wait_for_idle()
```

Fragile assertions:

```python
assert screenshot_matches("entire_desktop.png")
```

Screenshots are excellent diagnostics. They should not be the primary truth unless the purpose of the test is visual rendering.

---

## CI experience

A CI job should be able to run:

```bash
xvfb-run -a pytest tests/gui
```

On failure, the harness should capture:

```text
latest-state.json
widgets.jsonl
xwininfo-tree.txt
visible-windows.txt
screen.xwd
application stdout/stderr
application logs, if configured
```

The first diagnostic question should be answerable quickly:

```text
Did the expected widget exist?
Was it managed/sensitive/realized?
Where was it on screen?
What windows were visible?
What did the screen look like?
```

---

## What success looks like

A successful rollout is not necessarily hundreds of pixel-perfect GUI tests.

A successful rollout looks like:

- Every major workflow has a smoke test.
- Tests are readable Python.
- Most clicks are widget-path clicks.
- Generated low-confidence lines are reviewed.
- Failures produce useful diagnostics.
- The application code is unchanged or minimally changed.
- The team gradually adds stronger application-level assertions.
