# Purpose and non-goals

Motif Tap Harness exists to make GUI regression testing feasible for legacy Xt/Motif applications where large code changes are risky, expensive, or politically difficult.

The project is built around a pragmatic observation:

```text
A human can already perform the workflow.
Xnee can record the low-level input.
Xt/Motif can describe the widget tree.
A translator can combine those two streams into maintainable tests.
```

---

## Primary purpose

The primary purpose is to convert manual workflows into reviewable Python tests with minimal changes to the application under test.

The desired end state is:

```python
app.click("myApp.mainWindow.form.applyButton")
app.type_text("/tmp/input.dat")
app.press("Return")
assert Path("/tmp/output.dat").exists()
```

not:

```text
replay mouse coordinates forever
```

---

## Why this matters

Legacy Motif applications often contain important business logic and operational workflows, but they may lack modern test infrastructure. Teams may be afraid to change them because there is no safety net.

This project helps create that safety net incrementally:

```text
start with smoke workflows
lift recordings into Python
add assertions
run under Xvfb/CI
improve names and helpers over time
```

---

## Non-goals

This project is not trying to be:

```text
a full Motif replacement
a pixel-perfect visual testing framework
a complete accessibility layer
a generic cross-platform GUI automation framework
a long-term raw Xnee replay system
a way to avoid writing assertions
```

---

## Philosophy

The project should be useful before it is perfect.

A generated test with a few low-confidence comments is still valuable if it captures a workflow that previously had no automation.

The system should always be honest about uncertainty. When a click maps cleanly to an `XmPushButton`, generate a clean `app.click(path)`. When a click lands in a drawing area or ambiguous container, generate a reviewable fallback and mark it clearly.

---

## Success criteria

A successful adoption looks like:

- Critical workflows are covered by GUI smoke tests.
- Generated tests are readable and version controlled.
- Raw Xnee files are capture artifacts, not the main test format.
- Test failures produce useful diagnostics.
- Most tests assert real behavior, not just that windows appeared.
- Application source changes are optional and small.
- The team gains confidence to refactor or modernize safely.
