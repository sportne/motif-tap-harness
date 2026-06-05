# Motif Tap Harness

Motif Tap Harness is a starter project for turning manual workflows in legacy
X11/Xt/Motif applications into maintainable Python GUI tests.

It records user input with Xnee, observes the live Xt widget tree with a small
preload hook, and translates coordinate-heavy recordings into tests that click
stable widget paths.

```python
app.click("myApp.mainWindow.form.applyButton")
app.type_text("/tmp/input.dat")
app.press("Return")
```

## Status

This is an alpha-quality testing harness, not a finished product. The project
currently includes:

- a C `LD_PRELOAD` hook for observing Xt widgets,
- a Python replay harness backed by `xdotool`,
- Xnee normalization and translation commands,
- unit tests for the translator and widget matching logic,
- a small Motif calculator fixture,
- a containerized live-loop demo that records, translates, replays, and asserts
  `7 * 6 = 42`.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

make lint
make format-check
make test
make -C c
```

Or run the full fast baseline:

```bash
make doctor
make check
```

The C hook build produces `c/libxttap.so`.

## CLI Commands

Installed commands:

```text
motif-record
motif-normalize-xnee
motif-translate
motif-inspect-state
```

A typical workflow is:

```bash
motif-record --name open_valid_file --tap-so ./c/libxttap.so --app ./my_motif_app
motif-normalize-xnee recordings/open_valid_file/xnee-human.txt \
  --out recordings/open_valid_file/events.jsonl
motif-translate recordings/open_valid_file \
  --out tests/test_open_valid_file.py \
  --app ./my_motif_app
```

## Live-Loop Demo

The live-loop demo runs a real Motif calculator under Xvfb in a container.

```bash
docker build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
docker run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

Podman works with the same Dockerfile:

```bash
podman build -f containers/live-loop/Dockerfile -t motif-tap-live-loop .
podman run --rm motif-tap-live-loop scripts/live-loop-demo.sh
```

See [`docs/ci.md`](docs/ci.md) for artifact preservation, troubleshooting, and
CI guidance. The `live-loop` GitHub Actions workflow runs automatically for
changes to harness, hook, calculator fixture, package metadata, script,
container, test, and workflow files, and can also be run manually.

## Documentation

Start with [`docs/README.md`](docs/README.md). The main references are:

- [`docs/purpose.md`](docs/purpose.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/recording-and-translation.md`](docs/recording-and-translation.md)
- [`docs/generated-test-dsl.md`](docs/generated-test-dsl.md)
- [`docs/xt-hook-design.md`](docs/xt-hook-design.md)
- [`docs/limitations.md`](docs/limitations.md)
- [`docs/roadmap.md`](docs/roadmap.md)

Task planning lives in [`tasks/README.md`](tasks/README.md).

## License

BSD 3-Clause. See [`LICENSE`](LICENSE).
