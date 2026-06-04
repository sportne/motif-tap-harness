# Task: Translation Review Report

Status: Proposed
Type: AFK
Depends on: None

## Description

Make translation output reviewable without opening the generated pytest first.
`motif-translate` should optionally emit a compact report that lists each
translated action, its confidence, and the reason. CI should also be able to
fail when the translation contains TODO actions.

## Allowed Changes

- `src/motiftap/translator.py`
- `src/motiftap/commands/translate.py`
- `tests/**` for translator and CLI tests.
- `docs/recording-and-translation.md`
- `docs/user-experience.md`
- `tasks/**` to update task status.

## Barred Changes

- Do not change the generated test DSL beyond report-related metadata.
- Do not require screenshots for the first report version.
- Do not relax confidence rules to reduce TODO counts artificially.
- Do not add an HTML dependency; Markdown or plain text is sufficient.

## Acceptance Criteria

- [ ] `motif-translate --report <path>` writes a review report.
- [ ] The report lists every rendered action with operation, confidence, reason,
      and relevant widget path or root coordinate.
- [ ] The report includes summary counts for HIGH, MEDIUM, LOW, and TODO.
- [ ] `motif-translate --fail-on-todo` exits nonzero when TODO actions are
      present and still writes requested output artifacts.
- [ ] Tests cover report content, confidence counts, no-TODO success, and
      TODO-gated failure.

## Validation Required

```bash
make lint
make format-check
make test
```

Optional example check:

```bash
motif-translate examples/recordings/open_valid_file \
  --out /tmp/test_open_valid_file.py \
  --report /tmp/open_valid_file-report.md
```

## Notes

- The report should optimize for code review: short lines, stable ordering, and
  explicit LOW/TODO visibility.
- Keep before/after screenshots as a future enhancement unless they can be
  added without broadening the harness.
