# Recording and translation

This document describes the workflow from a manual session to a generated Python test.

---

## Recording directory contract

A recording directory should contain:

```text
meta.json
widgets.jsonl
latest-state.json
xnee.xns
xnee-human.txt
events.jsonl
```

Required for translation:

```text
meta.json
widgets.jsonl
events.jsonl
```

Optional but useful:

```text
latest-state.json
xnee.xns
xnee-human.txt
screenshots
logs
```

---

## `meta.json`

Example:

```json
{
  "record_start_monotonic": 1000.0,
  "app": ["./my_motif_app", "--test-mode"],
  "created_unix_time": 1770000000.0,
  "tap_so": "./c/libxttap.so"
}
```

The important field is `record_start_monotonic`. Xnee event times are treated as relative to the start of recording, while hook snapshots use monotonic process time. The translator adds the start offset so both streams share a timeline.

---

## `events.jsonl`

Normalized input events.

```json
{"t": 0.200, "kind": "button", "phase": "press", "button": 1, "x": 110, "y": 50}
{"t": 0.260, "kind": "button", "phase": "release", "button": 1, "x": 110, "y": 50}
{"t": 0.500, "kind": "key", "phase": "press", "key": "Return"}
```

Times are seconds relative to recording start.

---

## `widgets.jsonl`

Timestamped widget snapshots.

```json
{"type":"snapshot","t":1000.0,"widgets":[...]}
{"type":"snapshot","t":1000.3,"widgets":[...]}
```

Times are monotonic seconds. They need to overlap the normalized event times after adding `record_start_monotonic`.

---

## Translation logic

### Step 1: coalesce raw events

```text
press/release at nearly same coordinate -> click
printable key stream                   -> type_text
non-printable key press                -> press
```

### Step 2: hit-test clicks

For each click:

```text
snapshot = timeline.snapshot_at(click_time)
widget = deepest widget containing click.x, click.y
```

### Step 3: assign confidence

```text
HIGH    common activatable classes
MEDIUM  deep widget path but less clear class
LOW     parent-relative fallback
TODO    no match or unsupported gesture
```

### Step 4: generate Python

```python
app.click("myApp.mainWindow.form.applyButton")
app.type_text("/tmp/input.dat")
app.press("Return")
```

---

## Handling text input

The starter coalescer turns a stream of printable key events into `type_text`.

Example:

```text
slash t m p slash f o o
```

becomes:

```python
app.type_text("/tmp/foo")
```

You may need to adjust key normalization for keyboard layout, shifted characters, or Xnee's key naming.

---

## Handling menus

Menus can be translated as widget clicks if the hook sees the popup hierarchy:

```python
app.click("myApp.mainWindow.menuBar.fileMenu")
app.click("myApp.fileMenu.openItem")
```

For long-term stability, keyboard paths are often better:

```python
app.press("Alt+f")
app.press("o")
```

The generated test can be manually edited either way.

---

## Handling drawing areas

Drawing areas often represent application-specific canvases.

The translator may produce:

```python
app.click_relative("myApp.mainWindow.drawingArea", 183, 72)
```

That is acceptable as a starting point, but domain-specific helpers are better:

```python
app.canvas_click_node("A17")
```

or:

```python
app.canvas_click_world_coordinate(10.5, 42.0)
```

Those helpers require application knowledge and should be added gradually.

---

## Regeneration model

You can keep raw recordings for traceability, but generated tests should be reviewed and committed.

Recommended:

```text
commit tests/test_open_valid_file.py
optionally archive recordings/open_valid_file/ for later regeneration
```

Avoid:

```text
raw Xnee recordings as the only regression artifact
```

---

## Translation report idea

A future HTML report should show:

```text
Action 1: click 842,416 -> myApp.mainWindow.form.applyButton [HIGH]
Action 2: key Return -> app.press("Return") [HIGH]
Action 3: click 517,300 -> myApp.mainWindow.drawingArea +183,+72 [LOW]
```

That report would make reviews faster.
