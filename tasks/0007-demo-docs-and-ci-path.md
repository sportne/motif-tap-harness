# Task: Demo Docs And CI Path

Status: Done
Type: AFK
Depends on: 0006

## Description

Document the full live-loop demo and provide an optional CI path for running it
separately from fast unit tests. This makes the proof reproducible for future
contributors without making every quick test run start Xvfb and a Motif app.

## Allowed Changes

- `README.md`
- `docs/**`
- `.github/workflows/**`
- `scripts/**` for small command wrappers only.
- `tasks/**` to mark completed tasks and add follow-up notes.

## Barred Changes

- Do not make the live GUI loop part of the default fast unit-test path unless
  a separate decision is made.
- Do not remove existing local development instructions.
- Do not require Docker if Podman can run the same documented workflow.
- Do not commit bulky runtime artifacts.

## Acceptance Criteria

- [x] Documentation shows the full Docker and Podman commands for the live-loop
      demo.
- [x] Documentation lists expected artifacts and where they are written.
- [x] Troubleshooting covers missing Motif packages, Xvfb startup failures,
      `cnee` parser mismatches, hook state missing widgets, and replay timing.
- [x] The docs clearly distinguish fast unit checks from the slower live GUI
      proof.
- [x] Optional GitHub Actions wiring runs the live-loop job separately from the
      existing `ci` test job.
- [x] Task statuses are updated for completed work.

## Validation Required

```bash
make lint
make format-check
make test
make -C c

docker run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

If a GitHub Actions workflow is added, validate its syntax by inspection and by
running the same commands locally in the container.

## Notes

- Keep the top-level README concise; put detailed troubleshooting in
  `docs/ci.md` or a dedicated live-loop doc.
- If CI runtime is too slow for every pull request, document manual or scheduled
  invocation first.
