# Task: Automated Live Loop Gate

Status: Proposed
Type: AFK
Depends on: 0008

## Description

Run the live-loop proof automatically when relevant changes are made, while
keeping the fast CI path separate. The automated gate should exercise the
containerized record, normalize, translate, replay, and assertion loop and
upload useful artifacts on failure.

## Allowed Changes

- `.github/workflows/live-loop.yml`
- `.github/workflows/ci.yml` only for coordination with the fast baseline.
- `scripts/**` for small live-loop reliability or artifact improvements.
- `docs/ci.md`
- `README.md` for a concise CI pointer.
- `tasks/**` to update task status.

## Barred Changes

- Do not make every documentation-only change run the live-loop job.
- Do not merge the live-loop job into the fast unit-test job.
- Do not remove manual `workflow_dispatch` support.
- Do not commit live-loop runtime artifacts.

## Acceptance Criteria

- [ ] The live-loop workflow runs automatically for relevant changes to
      `c/**`, `src/motiftap/**`, `scripts/live-loop-*.sh`,
      `containers/live-loop/**`, tests, and workflow files.
- [ ] The workflow keeps `workflow_dispatch` support for manual runs.
- [ ] Artifacts are uploaded on success and failure, with failure logs easy to
      find.
- [ ] The workflow has a sensible timeout and concurrency policy.
- [ ] Documentation explains when the live-loop gate runs and how to reproduce
      it locally.

## Validation Required

```bash
make lint
make format-check
make test
make -C c
```

If Docker or Podman is available:

```bash
docker build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
docker run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

## Notes

- This task depends on task 0008 so the fast baseline is clear before adding a
  slower automated gate.
- Use path filters to avoid spending CI time on unrelated documentation-only
  edits.
