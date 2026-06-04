# Task: Xt Hook Path Stability

Status: Proposed
Type: AFK
Depends on: None

## Description

Harden the Xt hook enough that widget paths remain useful on real applications
with repeated child names or noisier widget updates. Duplicate sibling names
should be disambiguated, hook installation failures should not crash silently,
and snapshot writing should avoid excessive churn.

## Allowed Changes

- `c/xttap.c`
- `c/Makefile` only for compiler flags needed by the hook changes.
- `tests/**` if hook-output parsing tests are added.
- `scripts/live-loop-hook-smoke.sh`
- `docs/xt-hook-design.md`
- `docs/limitations.md`
- `tasks/**` to update task status.

## Barred Changes

- Do not replace the LD_PRELOAD hook architecture.
- Do not require changes to application source code.
- Do not remove existing path fields from hook JSON.
- Do not add a heavyweight C test framework.

## Acceptance Criteria

- [ ] Siblings with duplicate Xt names produce stable, disambiguated paths.
- [ ] Existing unique widget paths remain unchanged where possible.
- [ ] Missing `dlsym(RTLD_NEXT, ...)` targets fail or log clearly without
      undefined calls through null function pointers.
- [ ] Optional hook debug logging can be enabled through an environment
      variable and is quiet by default.
- [ ] Snapshot writes are debounced or otherwise limited enough to reduce log
      churn during rapid widget changes.
- [ ] The calculator hook smoke still passes and expected calculator widget
      paths remain discoverable.

## Validation Required

```bash
make -C c
make lint
make format-check
make test
```

If the live-loop image is available:

```bash
docker run --rm motif-tap-live-loop scripts/live-loop-hook-smoke.sh
```

## Notes

- Preserve the simple JSON snapshot contract consumed by `WidgetTimeline`.
- A path suffix such as an index is acceptable if it is deterministic and
  documented.
- Keep platform-specific portability work limited to what is needed for these
  stability improvements.
