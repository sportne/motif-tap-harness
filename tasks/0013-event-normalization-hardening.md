# Task: Event Normalization Hardening

Status: Done
Type: AFK
Depends on: None

## Description

Expand practical keyboard and event coverage while preserving the current
minimal event model. The normalizer and coalescer should handle common
printable keys, modifiers, shifted characters, malformed local `cnee` variants,
and unsupported gestures in a reviewable way.

## Allowed Changes

- `src/motiftap/events.py`
- `src/motiftap/xnee_normalize.py`
- `src/motiftap/commands/normalize_xnee.py`
- `tests/**` for focused normalizer and coalescer tests.
- `docs/recording-and-translation.md`
- `docs/limitations.md`
- `tasks/**` to update task status.

## Barred Changes

- Do not change the normalized JSONL schema unless unavoidable and documented.
- Do not add a full keyboard layout engine.
- Do not make unsupported gestures look higher-confidence than they are.
- Do not add a new recorder backend.

## Acceptance Criteria

- [x] Printable key handling covers common names used by `cnee`, including
      shifted punctuation where practical.
- [x] Modifier key sequences such as Alt menu shortcuts remain replayable as
      explicit key presses when they are not text input.
- [x] Drag and unsupported mouse gestures remain explicit TODO-style actions
      instead of being silently dropped.
- [x] Malformed or unknown input lines do not crash normalization unless the
      line claims to be structured JSONL.
- [x] Tests cover shifted text, common printable names, modifiers, drag
      fallback, malformed human-output lines, and local `cnee` variants.

## Validation Required

```bash
make lint
make format-check
make test
```

Optional example check:

```bash
motif-normalize-xnee examples/recordings/open_valid_file/xnee-human.txt \
  --out /tmp/open_valid_file-events.jsonl \
  --stats
```

## Notes

- Keep the normalized JSONL format as the stable interface for translator code.
- Prefer targeted mappings for common `cnee` output over broad keyboard-layout
  inference.
