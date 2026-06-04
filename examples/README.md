# Examples

This directory contains a tiny synthetic recording used by the unit tests and documentation.

It does not launch a real Motif application. Its purpose is to show the expected recording directory structure and the style of generated test output.

Try regenerating the example test:

```bash
PYTHONPATH=src python -m motiftap.commands.translate \
  examples/recordings/open_valid_file \
  --out /tmp/test_open_valid_file.py \
  --app ./examples/fake_motif_app --test-mode
```

Then inspect:

```bash
cat /tmp/test_open_valid_file.py
```

The generated test will not run until you replace `./examples/fake_motif_app` with a real application and have a working X11/Xt hook environment.

## Motif calculator fixture

`examples/motif_calc/` contains a small real Motif calculator used by the
containerized live-loop demo. It is intentionally simple: it exposes named
widgets for digits, operations, clear, equals, and the display, and writes the
latest result to `/tmp/motif-calc/result.txt` for replay assertions.

Build it with:

```bash
make -C examples/motif_calc
```

The live-loop container includes the Motif and X11 development packages needed
to build it.
