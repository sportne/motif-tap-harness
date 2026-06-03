#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m motiftap.commands.translate \
  examples/recordings/open_valid_file \
  --out /tmp/test_open_valid_file.py \
  --app ./examples/fake_motif_app --test-mode

echo
cat /tmp/test_open_valid_file.py
