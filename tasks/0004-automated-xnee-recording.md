# Task: Automated Xnee Recording

Status: Proposed
Type: AFK
Depends on: 0003

## Description

Create a deterministic recording flow that uses `motif-record` and scripted
`xdotool` input to capture a calculator workflow through `cnee`. This replaces
manual clicking with a repeatable CI-friendly path while still exercising the
same recording pipeline.

## Allowed Changes

- `scripts/**` for recording automation.
- `tests/gui/**` for optional pytest coverage of the recording script.
- `containers/live-loop/**` for invoking the recording script.
- `src/motiftap/xnee_normalize.py` only if the container's actual
  `cnee --human-printout` output requires parser support.
- `tests/**` for focused normalizer tests if parser support is added.

## Barred Changes

- Do not bypass `motif-record` by hand-writing recording files.
- Do not commit full generated recordings unless a later task explicitly asks
  for a small fixture.
- Do not replace `cnee` with a different recorder in this task.
- Do not change replay harness behavior.

## Acceptance Criteria

- [ ] A script starts Xvfb, starts a window manager, starts `motif-record`, and
      launches the calculator with the Xt hook.
- [ ] The script drives a deterministic expression with `xdotool`; use
      `7 * 6 =` as the default workflow.
- [ ] The script stops recording without requiring human keyboard input.
- [ ] The recording directory contains `meta.json`, `xnee-human.txt`,
      `events.jsonl`, `widgets.jsonl`, and `latest-state.json`.
- [ ] Normalization reports non-zero button events and no obvious parser
      failure.
- [ ] The script prints the recording directory path and confidence-relevant
      event counts.

## Validation Required

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-record.sh
```

Inspect the printed recording directory and confirm:

```bash
test -s "$RECORDING_DIR/meta.json"
test -s "$RECORDING_DIR/xnee-human.txt"
test -s "$RECORDING_DIR/events.jsonl"
test -s "$RECORDING_DIR/widgets.jsonl"
test -s "$RECORDING_DIR/latest-state.json"
```

## Notes

- Prefer a temp directory such as `/tmp/motif-tap-live-loop/recordings`.
- If `motif-record` cannot currently stop non-interactively, implement the
  smallest CLI extension needed and test it directly.
- Keep timing waits condition-based where possible; use short sleeps only where
  X11 tooling needs startup settling.

