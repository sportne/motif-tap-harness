# Architecture

Motif Tap Harness is a record-and-lift system.

It does not attempt to replace the Motif toolkit, rewrite the application, or build a full Selenium-style object model. Instead, it combines two sources of information that are each incomplete on their own:

1. **Xnee recording**: what the user did at the X server level.
2. **Xt/Motif widget snapshots**: what semantic widget was under each coordinate when the user did it.

Together, they produce maintainable Python tests.

---

## System diagram

```text
                 ┌─────────────────────────────┐
                 │ Human uses Motif application │
                 └──────────────┬──────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
┌─────────▼─────────┐                       ┌─────────▼─────────┐
│ Xnee / cnee       │                       │ Xt tap hook        │
│ raw X input       │                       │ widget snapshots   │
│ mouse + keyboard  │                       │ names + geometry   │
└─────────┬─────────┘                       └─────────┬─────────┘
          │                                           │
          └─────────────────────┬─────────────────────┘
                                │
                       ┌────────▼────────┐
                       │ Normalized      │
                       │ event stream    │
                       └────────┬────────┘
                                │
                       ┌────────▼────────┐
                       │ Translator      │
                       │ coordinate →    │
                       │ widget path     │
                       └────────┬────────┘
                                │
                       ┌────────▼────────┐
                       │ Generated       │
                       │ Python tests    │
                       └────────┬────────┘
                                │
                       ┌────────▼────────┐
                       │ Replay harness  │
                       │ live lookup +   │
                       │ xdotool input   │
                       └─────────────────┘
```

---

## Data flow

### 1. Recording

The recorder launches the application with the hook enabled:

```bash
MOTIF_TAP_STATE=recordings/open_valid_file/latest-state.json \
MOTIF_TAP_LOG=recordings/open_valid_file/widgets.jsonl \
LD_PRELOAD=./c/libxttap.so \
./my_motif_app
```

In parallel, it starts `cnee` to capture mouse and keyboard activity.

Output directory:

```text
recordings/open_valid_file/
  meta.json
  latest-state.json
  widgets.jsonl
  xnee.xns
  xnee-human.txt
```

### 2. Normalization

Xnee output is converted to a stable JSON Lines format:

```json
{"t": 0.210, "kind": "button", "phase": "press", "button": 1, "x": 842, "y": 416}
{"t": 0.290, "kind": "button", "phase": "release", "button": 1, "x": 842, "y": 416}
{"t": 0.500, "kind": "key", "phase": "press", "key": "Return"}
```

This step isolates the rest of the project from Xnee version differences.

### 3. Translation

The translator coalesces raw events into actions:

```text
ButtonPress + ButtonRelease -> click
printable key stream       -> type_text
non-printable key press    -> press
```

For each click, it asks the widget timeline:

```text
At timestamp T, which deepest managed/sensitive widget contained root coordinate X,Y?
```

Then it emits Python:

```python
app.click("myApp.mainWindow.form.applyButton")
```

If the hit test is uncertain, it emits a reviewable fallback:

```python
app.click_relative("myApp.mainWindow.drawingArea", 183, 72)
# LOW: parent-relative fallback inside XmDrawingArea
```

### 4. Replay

Generated tests use `MotifApp` from `src/motiftap/harness.py`.

At runtime:

```python
app.click("myApp.mainWindow.form.applyButton")
```

means:

1. Read the current `latest-state.json`.
2. Find the widget path.
3. Compute its current center in root coordinates.
4. Use `xdotool` to move and click.

This is why a generated test can survive window movement.

---

## Major components

### `c/xttap.c`

A starter LD_PRELOAD hook for Xt applications. It observes widget changes and writes JSON snapshots.

Important responsibilities:

- Track top-level roots.
- Walk Xt composite children.
- Record widget path, class, window id, geometry, managed state, sensitivity, and realization state.
- Write an atomic current state file.
- Append timestamped snapshots to a JSONL log.

### `src/motiftap/widget_map.py`

Loads snapshots and performs hit testing.

Important class:

```python
WidgetTimeline
```

### `src/motiftap/events.py`

Defines normalized raw input events and coalesces them into higher-level actions.

### `src/motiftap/xnee_normalize.py`

Converts local Xnee/cnee output to normalized JSONL. This is intentionally small and designed to be customized once for your local Xnee output format.

### `src/motiftap/translator.py`

Converts normalized events and widget snapshots into Python test code.

### `src/motiftap/harness.py`

Runtime harness used by generated tests.

---

## Why the live state file matters

The translator uses the recording-time widget log, but replay uses the runtime state file.

That distinction is critical:

```text
Recording time:
  click at 842,416 -> myApp.mainWindow.form.applyButton

Replay time:
  where is myApp.mainWindow.form.applyButton now?
  click its current center
```

The test does not reuse the old root coordinate unless it has no better option.

---

## Confidence levels

The generated code annotates each action:

```text
HIGH    activatable widget class such as PushButton, Text, List, ToggleButton
MEDIUM  deep widget path, but class is less clearly activatable
LOW     parent-relative fallback, usually drawing areas or container widgets
TODO    no widget match or unsupported gesture
```

A human reviewer should focus on `LOW` and `TODO` lines first.

---

## Design principle

The project should be useful even when it is imperfect.

A good first run might translate 80% of clicks cleanly, mark 15% as parent-relative, and leave 5% as TODO. That is still much faster than writing an entire GUI automation suite by hand.
