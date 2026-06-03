# Task: Container Live Loop Base

Status: Proposed
Type: AFK
Depends on: None

## Description

Add a Docker/Podman-compatible container setup for the live Motif/X11 loop. The
container should provide a predictable Debian or Ubuntu environment with Xvfb,
a lightweight window manager, X11 input tooling, `cnee`, Motif development
headers, C build tooling, and Python dev tooling.

This task proves the repository can be built and checked inside the same kind
of environment that will later run the live GUI demo.

## Allowed Changes

- `containers/live-loop/**`
- `scripts/**` for container helper scripts only.
- `docs/**` only if a short pointer to the new container entry point is needed.
- `Makefile` only for non-invasive convenience targets that call the container
  build or checks.

## Barred Changes

- Do not change `src/motiftap/**` behavior.
- Do not change `c/xttap.c` behavior.
- Do not add the calculator application in this task.
- Do not add generated recordings or generated GUI tests.
- Do not require Docker-only syntax that prevents Podman from building the same
  Dockerfile.

## Acceptance Criteria

- [ ] `containers/live-loop/Dockerfile` builds with Docker or Podman.
- [ ] The image installs `libmotif-dev`, `libxt-dev`, `libx11-dev`, `xvfb`,
      `openbox`, `xdotool`, `xnee`, `gcc`, `make`, and Python tooling.
- [ ] The image can install the project in editable dev mode.
- [ ] The image can build `c/libxttap.so`.
- [ ] The image can run the repository's unit tests and Ruff checks.
- [ ] The task documents the exact build command for Docker and Podman.

## Validation Required

```bash
docker build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
# or:
podman build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .

docker run --rm motif-tap-live-loop make lint
docker run --rm motif-tap-live-loop make format-check
docker run --rm motif-tap-live-loop make test
docker run --rm motif-tap-live-loop make -C c
```

If Podman is the available runtime, run the equivalent `podman run --rm`
commands.

## Notes

- Prefer a current Debian or Ubuntu base image with apt packages available in
  the default repositories.
- Keep the image focused on the live-loop demo rather than becoming a general
  development image.
- Do not start Xvfb in the Dockerfile build stage; runtime scripts should start
  Xvfb when needed.

