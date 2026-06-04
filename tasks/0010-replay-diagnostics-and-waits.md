# Task: Replay Diagnostics And Waits

Status: Done
Type: AFK
Depends on: None

## Description

Improve `MotifApp` replay reliability and failure visibility while keeping the
generated test DSL small. Input failures should explain what command failed,
diagnostics should be captured at the point of failure, and tests should have a
small condition-based wait helper for application-specific assertions.

## Allowed Changes

- `src/motiftap/harness.py`
- `tests/**` for focused harness tests.
- `docs/generated-test-dsl.md`
- `docs/ci.md` if diagnostics behavior changes.
- `tasks/**` to update task status.

## Barred Changes

- Do not add a Selenium-style object model.
- Do not introduce a GUI automation dependency beyond the existing `xdotool`
  approach.
- Do not change generated translator output except where documentation examples
  need to mention the new wait helper.
- Do not make screenshots or image comparison part of the core DSL.

## Acceptance Criteria

- [x] Missing `DISPLAY` fails with a clear `MotifApp` startup error.
- [x] Failed `xdotool` calls include the command, return code, stdout, and
      stderr in the raised exception.
- [x] `click`, `click_relative`, `click_root`, `press`, and `type_text` capture
      diagnostics when their underlying input command fails.
- [x] `MotifApp.wait_until(description, predicate, timeout=None)` is available
      for simple condition-based waits.
- [x] Tests cover missing display validation, wrapped `xdotool` failure output,
      diagnostics capture on input failure, and `wait_until` success/timeout.

## Validation Required

```bash
make lint
make format-check
make test
```

## Notes

- Keep the new wait helper generic and small; callers provide the predicate.
- Preserve existing `wait_for_widget` and `wait_for_window` behavior.
- Do not require a real X server for the new unit tests; mock subprocess and
  filesystem behavior where practical.
