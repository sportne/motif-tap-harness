# Limitations

Motif Tap Harness is useful, but it is not magic. This document lists the main limitations so teams can plan around them.

---

## LD_PRELOAD limitations

The preload hook may not work when:

```text
the application is statically linked
the application is setuid or otherwise security-restricted
the platform loader disables LD_PRELOAD
the application uses a different Xt library than the hook was built against
the application initializes Xt in a path not yet intercepted by the starter hook
```

Mitigation:

```text
use a linked-in hook
wrap more Xt initialization functions
install Xt hooks from application startup code
```

---

## Custom drawing

A drawing area may be one large widget containing application-specific content.

The hook can say:

```text
click happened inside myApp.mainWindow.drawingArea at +183,+72
```

It cannot know that the coordinate corresponds to:

```text
node A17
row 42
map feature "Pump Station 3"
waveform marker 10.5s
```

Mitigation:

```text
add application-specific helpers
assert domain outputs
expose model state through a test-only API
use image matching only where appropriate
```

---

## Drag-and-drop

The starter coalescer detects simple clicks. Drag gestures are marked for review.

Mitigation:

```text
write explicit drag helpers
prefer keyboard alternatives
add domain-specific canvas operations
```

---

## Duplicate widget names

Xt paths are weaker when siblings share names.

Example:

```text
myApp.dialog.form.button[0]
myApp.dialog.form.button[1]
```

The hook adds indexes only for duplicate sibling names, so existing unique paths
stay shorter.

Mitigation:

```text
improve widget names in source or GUI builder
add alias mapping
```

---

## Timing

The translator assumes Xnee event times can be aligned with hook snapshot times.

If timestamps do not line up, hit testing may use the wrong snapshot.

Mitigation:

```text
record monotonic start time carefully
include synchronization markers
write snapshots frequently during recording
compare final screenshots and logs when debugging
```

---

## Menus and grabs

Motif menus may involve popup shells, grabs, and transient windows. Pointer replay can be flaky.

Mitigation:

```text
prefer keyboard menu traversal
use accelerators/mnemonics
wait for popup widgets before clicking them
```

---

## Keyboard layout

Text normalization may depend on keyboard layout and Xnee key naming.

The starter handles common printable names and simple modifier shortcuts, but it
does not implement a full keyboard layout engine.

Mitigation:

```text
convert printable key streams to type_text
standardize locale and keyboard layout in CI
customize xnee_normalize.py for local output
```

---

## Visual assertions

Screenshots are sensitive to fonts, themes, colors, antialiasing, and window manager differences.

Mitigation:

```text
use screenshots as diagnostics
assert behavior through files/logs/domain state
restrict image comparison to rendering-specific tests
```

---

## Not a substitute for application-level tests

GUI tests are valuable, but they are slower and more brittle than unit or integration tests.

The best test portfolio is layered:

```text
unit tests for logic
integration tests for data/model behavior
GUI smoke tests for critical workflows
special visual tests only where needed
```
