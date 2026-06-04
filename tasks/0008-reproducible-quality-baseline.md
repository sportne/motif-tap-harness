# Task: Reproducible Quality Baseline

Status: Proposed
Type: AFK
Depends on: None

## Description

Make the advertised fast quality baseline reproducible for a new contributor
and in CI. The project should clearly distinguish missing local dependencies
from real test failures, and the fast path should cover linting, formatting,
unit tests, and the Xt hook build.

## Allowed Changes

- `Makefile`
- `.github/workflows/**`
- `docs/**` for short setup or CI documentation updates.
- `README.md` for concise quick-start command updates.
- `tests/**` only for tests that validate any new lightweight helper command.
- `tasks/**` to update task status.

## Barred Changes

- Do not change `src/motiftap/**` runtime behavior.
- Do not change `c/xttap.c` behavior.
- Do not make the live-loop demo part of the default fast check.
- Do not require Docker or Podman for the fast baseline.

## Acceptance Criteria

- [ ] A single fast command, such as `make check`, runs lint, format-check,
      unit tests, and the C hook build.
- [ ] A local dependency check, such as `make doctor`, reports missing Python
      dev tools, compiler/X11 headers, and common GUI tools with actionable
      messages.
- [ ] GitHub Actions fast CI runs lint, format-check, unit tests, and the C hook
      build.
- [ ] Documentation identifies the intended local setup command sequence and
      explains the difference between fast checks and the live-loop proof.

## Validation Required

```bash
make doctor
make check
make lint
make format-check
make test
make -C c
```

## Notes

- Keep the commands thin wrappers around existing checks where possible.
- If a dependency is optional for normal unit tests, report it as optional
  rather than failing the whole doctor command.
- The current local workspace has a `.venv` that passes tests and Ruff checks;
  plain system `python3` may not have pytest or Ruff installed.
