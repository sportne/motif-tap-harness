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
