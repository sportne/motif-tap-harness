# Test automation approach

Motif Tap Harness is based on a layered test strategy.

The goal is not to perfectly model every Motif widget. The goal is to create a practical regression testing system for legacy applications where large code changes are undesirable.

---

## Layer 1: controlled X11 environment

Run GUI tests in a predictable environment.

Recommended defaults:

```text
fixed screen size
fixed color depth
fixed locale
fixed fonts
fixed Motif resource files
same or similar window manager
known test data directory
clean application preferences
```

For CI:

```bash
xvfb-run -a pytest tests/gui
```

If the application depends on window-manager behavior, run a lightweight window manager inside Xvfb before launching tests.

---

## Layer 2: record manual workflows

Use Xnee/cnee as a capture mechanism.

Xnee is not the long-term test format. It is the way to capture workflows quickly from people who already know the application.

Good recording candidates:

```text
open valid file
open invalid file
run default operation
change preference
create simple object
save output
print/export/report
cancel operation
handle validation dialog
```

Bad first candidates:

```text
complex drag-and-drop editing
freehand drawing
pixel-perfect rendering
long exploratory sessions
workflows with nondeterministic data
```

---

## Layer 3: lift coordinates to widget paths

The translator maps root coordinates to widgets using the Xt snapshot timeline.

Example:

```text
Raw event:
  ButtonPress at root 842,416

Widget map at that time:
  myApp.mainWindow.form.applyButton
    root_x=818 root_y=392 width=96 height=32

Generated test:
  app.click("myApp.mainWindow.form.applyButton")
```

This is the core value of the project.

---

## Layer 4: replay with live geometry

During replay, the test does not click the old coordinate.

It does this:

```python
widget = app.wait_for_widget("myApp.mainWindow.form.applyButton")
click(widget.current_center())
```

So if the window moves, the test still clicks the same widget.

---

## Layer 5: assert behavior

The generated interactions are only half of a good test. The other half is the assertion.

Prefer assertions in this order:

1. Domain result: output files, database rows, report contents, model state.
2. Application logs: success messages, error absence, operation IDs.
3. Dialog/window state: success dialog appeared, validation dialog appeared.
4. Widget state: button enabled, text field present, list item visible.
5. Screenshot/image comparison only where visual rendering is the purpose.

Example:

```python
def test_export_report():
    with MotifApp(["./my_app", "--test-mode"]) as app:
        app.click("myApp.mainWindow.exportButton")
        app.type_text("/tmp/report.txt")
        app.press("Return")

        assert Path("/tmp/report.txt").exists()
        assert "Total:" in Path("/tmp/report.txt").read_text()
```

---

## Layer 6: diagnostics

Every GUI test failure should produce enough context to debug without rerunning immediately.

Minimum diagnostics:

```text
screen capture
live widget state
widget snapshot log
window tree
visible window list
stdout/stderr
application logs
input data used by the test
```

The included harness captures some of these by default. Extend it for your application logs and domain artifacts.

---

## Stable naming strategy

The system is only as good as the widget paths it sees.

Best case:

```text
myApp.mainWindow.form.applyButton
```

Weak case:

```text
myApp.form.button.button.button
```

If you can make small source or GUI-builder changes, prefer stable widget/resource names:

```c
XtVaCreateManagedWidget(
    "applyButton",
    xmPushButtonWidgetClass,
    parent,
    XmNlabelString, label,
    NULL);
```

Even if you cannot change code now, the generated tests will reveal naming hotspots.

---

## What to automate first

Start with smoke workflows that produce concrete outputs.

Suggested first suite:

```text
test_app_launches
test_open_valid_file
test_open_invalid_file_shows_error
test_run_default_operation
test_save_output
test_cancel_dialog
test_preferences_round_trip
```

These tests are likely to be valuable and relatively stable.

---

## What not to automate first

Delay these until the harness is proven:

```text
highly graphical canvas operations
precise mouse drags
race-prone workflows
long multi-minute flows
print dialog behavior dependent on host configuration
workflows requiring external systems
```

---

## Maintenance model

The intended maintenance loop:

1. Record a workflow.
2. Generate a test.
3. Review low-confidence lines.
4. Add assertions.
5. Commit the Python test, not the raw Xnee recording as the primary artifact.
6. Keep raw recording and widget logs only when they help regenerate or debug.

---

## Rule of thumb

Use automation to capture the boring part: the manual sequence of clicks and keys.

Use humans to define the important part: what the application should have done.
