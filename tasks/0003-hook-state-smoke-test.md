# Task: Hook State Smoke Test

Status: Proposed
Type: AFK
Depends on: 0001, 0002

## Description

Prove the Xt preload hook observes the Motif calculator inside Xvfb. This is
the first live check that `LD_PRELOAD=c/libxttap.so` produces usable
`latest-state.json` and `widgets.jsonl` files for a real Motif process.

## Allowed Changes

- `scripts/**` for hook smoke-test scripts.
- `tests/gui/**` for optional pytest wrappers around the smoke test.
- `containers/live-loop/**` for invoking the smoke test.
- `docs/**` for a short reference to the smoke command.

## Barred Changes

- Do not change calculator behavior except to fix widget naming defects found by
  this task.
- Do not change translator output.
- Do not commit runtime-generated `latest-state.json` or `widgets.jsonl` files.
- Do not weaken the hook's JSON contract to make the smoke test pass.

## Acceptance Criteria

- [ ] A repeatable command launches the calculator under Xvfb with
      `LD_PRELOAD=c/libxttap.so`.
- [ ] `MOTIF_TAP_STATE` points to a non-empty `latest-state.json`.
- [ ] `MOTIF_TAP_LOG` points to a non-empty `widgets.jsonl`.
- [ ] `motif-inspect-state` lists meaningful calculator widget paths.
- [ ] The state includes digit buttons, operation buttons, equals/clear buttons,
      and the display/result widget.
- [ ] The command exits cleanly and kills the calculator, Xvfb, and window
      manager processes it started.

## Validation Required

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-hook-smoke.sh
```

The script must fail if required calculator widget paths are missing.

## Notes

- Use a temporary artifact directory under `/tmp`, not repository-tracked
  paths.
- If the hook misses widgets, record the observed state before deciding whether
  the fix belongs in the calculator naming, hook installation timing, or hook
  traversal.

