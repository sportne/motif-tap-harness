# Task: Motif Calculator App

Status: Done
Type: AFK
Depends on: 0001

## Description

Add a small real C Motif calculator application that can be used as the target
for live recording and replay. The calculator should support addition,
subtraction, multiplication, and division with named widgets so the Xt hook can
produce stable widget paths.

The calculator must write its latest result to a deterministic file so replay
tests can assert behavior without needing Motif label text introspection.

## Allowed Changes

- `examples/motif_calc/**`
- `examples/README.md`
- `Makefile` only for a convenience target that builds the calculator.
- `containers/live-loop/**` only if the container needs to build or install the
  calculator.

## Barred Changes

- Do not change `src/motiftap/**`.
- Do not change `c/xttap.c`.
- Do not add recording fixtures in this task.
- Do not make the calculator depend on non-Motif GUI frameworks.

## Acceptance Criteria

- [x] `examples/motif_calc/` contains C source and a Makefile.
- [x] The calculator builds inside the live-loop container.
- [x] The calculator launches under Xvfb.
- [x] It supports at least `+`, `-`, `*`, and `/`.
- [x] Widgets have explicit stable names for digits, operation buttons,
      equals/clear buttons, and result display.
- [x] Evaluating `7 * 6 =` writes `42` to `/tmp/motif-calc/result.txt`.
- [x] Division by zero produces a deterministic display/result value such as
      `ERR` and does not crash.

## Validation Required

```bash
docker run --rm motif-tap-live-loop make -C examples/motif_calc

docker run --rm motif-tap-live-loop sh -lc '
  Xvfb :99 -screen 0 1280x1024x24 &
  export DISPLAY=:99
  openbox &
  sleep 1
  examples/motif_calc/motif-calc &
  sleep 1
  xdotool search --name "Motif Calculator"
'
```

The exact binary name may differ, but it must be documented in the task update.

## Notes

- Use Motif/Xt widgets, not raw Xlib drawing, so the hook can inspect the UI.
- Prefer simple push buttons and a label/text field for the display.
- Keep calculator state intentionally small and deterministic.
