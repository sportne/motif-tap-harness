#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
make -C c || {
  echo "C hook build failed. Install libXt/libX11 development headers and retry." >&2
  exit 1
}
pytest
