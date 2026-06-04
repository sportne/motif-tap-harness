# Generated test DSL

Generated tests use the `MotifApp` harness.

Import:

```python
from motiftap.harness import MotifApp
```

Typical structure:

```python
def test_open_valid_file():
    with MotifApp(["./my_motif_app", "--test-mode"]) as app:
        app.wait_for_idle()
        app.click("myApp.mainWindow.form.openButton")
        app.type_text("/tmp/input.dat")
        app.press("Return")
        app.wait_for_widget("myApp.completeDialog.okButton")
        app.click("myApp.completeDialog.okButton")
```

---

## `MotifApp(argv)`

Launches the application with the Xt tap hook enabled.

```python
with MotifApp(["./my_app"]) as app:
    ...
```

Optional arguments:

```python
MotifApp(
    ["./my_app"],
    tap_so="./c/libxttap.so",
    timeout=10.0,
    keep_artifacts=True,
)
```

The hook path can also be provided through:

```bash
MOTIF_TAP_SO=/path/to/libxttap.so pytest
```

---

## `app.click(path)`

Clicks the current center of a widget path.

```python
app.click("myApp.mainWindow.form.applyButton")
```

Runtime behavior:

```text
read latest-state.json
find widget path
compute center from current root_x/root_y/width/height
xdotool mousemove/click
```

---

## `app.click_relative(path, x, y)`

Clicks a coordinate relative to a widget.

```python
app.click_relative("myApp.mainWindow.drawingArea", 183, 72)
```

Use this for drawing areas, canvases, or ambiguous container clicks.

---

## `app.click_root(x, y)`

Clicks an absolute root coordinate.

```python
app.click_root(842, 416)
```

This is a last resort. It is expected to be fragile.

Generated tests should mark this as `TODO`.

---

## `app.press(key)`

Sends a key through xdotool.

```python
app.press("Return")
app.press("Alt+f")
app.press("Escape")
```

Use keyboard navigation when it is more stable than pointer navigation.

---

## `app.type_text(text)`

Types text through xdotool.

```python
app.type_text("/tmp/input.dat")
```

This is usually better than replaying every individual character key event.

---

## `app.wait_for_widget(path)`

Waits until a widget exists and is visible enough to interact with.

```python
app.wait_for_widget("myApp.completeDialog.okButton")
```

This is the preferred synchronization primitive.

---

## `app.wait_for_window(title)`

Waits until a window title appears.

```python
app.wait_for_window("Complete")
```

Use this when the widget path is unavailable or less stable than the window title.

---

## `app.wait_until(description, predicate)`

Waits for an application-specific condition.

```python
app.wait_until(
    "output report",
    lambda: Path("/tmp/report.txt").exists(),
)
```

Use this for simple file, log, or domain-state conditions that are not visible
as Motif widgets.

---

## `app.capture_diagnostics(label)`

Captures debugging artifacts.

```python
app.capture_diagnostics("before_save")
```

The harness automatically captures diagnostics on context-manager failure.

---

## Extending the DSL

Application-specific helpers are encouraged.

Example:

```python
class MyApp(MotifApp):
    def open_file(self, path: str) -> None:
        self.press("Alt+f")
        self.press("o")
        self.type_text(path)
        self.press("Return")

    def run_default_operation(self) -> None:
        self.click("myApp.mainWindow.form.runButton")
        self.wait_for_widget("myApp.completeDialog.okButton")
```

Generated tests can then be refactored from:

```python
app.click("myApp.mainWindow.menuBar.fileMenu")
app.click("myApp.fileMenu.openItem")
app.type_text("/tmp/input.dat")
app.press("Return")
```

to:

```python
app.open_file("/tmp/input.dat")
```

That refactoring should happen after the generated tests prove the workflow.
