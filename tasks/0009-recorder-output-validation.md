# Task: Recorder Output Validation

Status: Done
Type: AFK
Depends on: None

## Description

Harden `motif-record` so recording failures are detected at the command
boundary. A failed application launch, failed `cnee` run, or empty required
output should produce a clear error before the user moves on to normalization
or translation.

## Allowed Changes

- `src/motiftap/commands/record.py`
- `tests/**` for focused command tests and helper fixtures.
- `docs/**` for short troubleshooting updates.
- `tasks/**` to update task status.

## Barred Changes

- Do not change the normalized event JSONL format.
- Do not change translation behavior.
- Do not add a new recording backend.
- Do not commit large raw recordings or runtime artifacts.

## Acceptance Criteria

- [x] `motif-record` validates that `meta.json`, `latest-state.json`, and
      `widgets.jsonl` exist and are non-empty before reporting success.
- [x] When `cnee` is used, `motif-record` validates that `xnee-human.txt` exists
      and is non-empty.
- [x] Non-zero app or `cnee` exits are reported with command context and a
      useful next step.
- [x] `--no-cnee` mode still supports hook debugging and validates only the
      hook-related outputs.
- [x] Focused tests cover successful validation, missing hook state, empty Xnee
      output, and failed subprocess exit.

## Validation Required

```bash
make lint
make format-check
make test
```

If the live-loop image is available:

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-record.sh
```

## Notes

- Keep validation close to the recorder command rather than adding a broader
  recording management layer.
- Prefer concise error messages that name the missing file and the likely cause,
  such as hook preload failure or `cnee` parser/permission issues.
