# Xt hook design

The Xt hook is the bridge between low-level X11 input and Motif widget semantics.

Xnee can tell us that the user clicked at a root coordinate. The hook tells us what Xt/Motif widget occupied that coordinate at the time.

---

## Goals

The hook should record enough information to support two workflows:

### Translation-time hit testing

```text
At time T, coordinate X,Y belonged to widget path P.
```

### Replay-time lookup

```text
Widget path P currently has root geometry X,Y,W,H.
```

---

## Output files

The hook writes two files.

### `latest-state.json`

The current widget tree. The replay harness reads this while tests run.

```json
{
  "type": "snapshot",
  "t": 1234.567,
  "widgets": [
    {
      "path": "myApp.mainWindow.form.applyButton",
      "name": "applyButton",
      "class": "XmPushButton",
      "window": "0x4600021",
      "root_x": 818,
      "root_y": 392,
      "width": 96,
      "height": 32,
      "managed": true,
      "sensitive": true,
      "realized": true,
      "depth": 4
    }
  ]
}
```

The file should be written atomically:

```text
write temp file
flush/fsync
rename temp to latest-state.json
```

### `widgets.jsonl`

A timestamped append-only log of snapshots.

```text
{"type":"snapshot","t":1234.100,"widgets":[...]}
{"type":"snapshot","t":1234.250,"widgets":[...]}
{"type":"snapshot","t":1234.900,"widgets":[...]}
```

The translator uses this file because it needs to know what the UI looked like at the moment each recorded event occurred.

---

## Widget fields

Required fields:

```text
path        stable hierarchical path where possible
name        Xt widget name
class       Xt widget class name
root_x      root-window X coordinate
root_y      root-window Y coordinate
width       widget width
height      widget height
depth       depth in Xt tree
managed     whether Xt considers it managed
sensitive   whether Xt considers it sensitive
realized    whether it has been realized
window      X window id if available, null otherwise
```

Optional future fields:

```text
label string
mnemonic
accelerator
resource values
screen number
display name
process id
parent path
sibling index
```

---

## LD_PRELOAD versus linked-in hook

### LD_PRELOAD mode

Pros:

```text
no application source change
fast to try
works well for dynamically linked applications
```

Cons:

```text
depends on dynamic linker behavior
harder to debug
not suitable for setuid/security-restricted binaries
may miss some initialization paths
```

### Linked-in mode

Pros:

```text
cleaner initialization
less fragile
can expose richer application-specific state
```

Cons:

```text
requires rebuild/source change
may need build-system changes
```

The Python side does not care which mode creates the JSON files.

---

## How the starter hook works

`c/xttap.c` uses three techniques:

1. It installs Xt hook callbacks when it sees a display.
2. It wraps common Xt functions such as `XtRealizeWidget`, `XtManageChild`, and `XtSetValues`.
3. It walks the Xt widget tree using Xt private structures.

The wrapper functions help bootstrap the hook even if the application initializes Xt in a way that is not intercepted early.

---

## Why private Xt headers are used

Xt does not provide a simple public API to enumerate all children of an arbitrary composite widget. The starter hook uses private headers to walk `CompositeWidget` children.

That is a pragmatic choice for a test-only tool. If this becomes production infrastructure, you may want to isolate platform differences behind compile-time checks.

---

## Geometry and root coordinates

The hook records root coordinates so the translator can perform hit testing against Xnee root coordinates.

For realized widgets, root coordinates are obtained through Xt coordinate translation. For unrealized widgets, the root coordinates are not meaningful and should not be used for hit testing.

---

## Motif gadgets

Some Motif controls are gadgets rather than full X windows. They may not have their own X window id. That is fine.

The test system needs geometry, not necessarily a window id.

```text
widget path + geometry is enough to click the current center
```

For windowless items, the harness still clicks the corresponding location in the parent window.

---

## Duplicate names

Xt allows sibling widgets to have duplicate names. This weakens path stability.

The starter hook does not yet add sibling indexes. A production version should generate paths like:

```text
myApp.dialog.form.button[0]
myApp.dialog.form.button[1]
```

only when duplicates exist.

The best fix is to improve widget names in the application or GUI builder configuration.

---

## Performance

The starter hook dumps the tree often. That is fine for initial experiments, but a large application may need throttling.

Future improvements:

```text
debounce snapshots
only dump after event-loop idle
write binary/protobuf internally and convert later
filter by realized widgets
track diffs instead of full snapshots
```

Start simple. Optimize only after measuring.

---

## Failure modes

The hook may not work when:

```text
the app is statically linked
the loader ignores LD_PRELOAD
the app does not use Xt/Motif for the relevant UI
the app creates direct Xlib child windows outside Xt
the app crashes due to interposition conflicts
private Xt headers differ on the target platform
```

In those cases, consider a linked-in hook or a smaller application-specific registry.
