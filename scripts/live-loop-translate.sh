#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop}"
RECORDING_DIR="${BASE_DIR}/recordings/${MOTIF_TAP_RECORDING_NAME:-calculator_multiply}"
OUTPUT_TEST="${ROOT_DIR}/tests/gui/test_calculator_multiply.py"

"${ROOT_DIR}/scripts/live-loop-record.sh"

mkdir -p "$(dirname "${OUTPUT_TEST}")"
motif-translate \
  "${RECORDING_DIR}" \
  --out "${OUTPUT_TEST}" \
  --test-name calculator_multiply \
  --app "${ROOT_DIR}/examples/motif_calc/motif-calc"

python - "${OUTPUT_TEST}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "from pathlib import Path" not in text:
    text = "from pathlib import Path\n" + text

assertion = "        assert Path('/tmp/motif-calc/result.txt').read_text(encoding='utf-8').strip() == '42'"
if assertion not in text:
    marker = "        # assert Path('/tmp/output.dat').exists()\n"
    text = text.replace(marker, marker + assertion + "\n")

text = text.replace("]) as app:", "], keep_artifacts=True) as app:")

path.write_text(text, encoding="utf-8")
PY

python -m ruff format "${OUTPUT_TEST}"

if ! grep -q 'motif-calc.calculatorForm.keypad.digit7' "${OUTPUT_TEST}"; then
  echo "Generated test is missing the digit7 widget-path click." >&2
  exit 1
fi
if ! grep -q '/tmp/motif-calc/result.txt' "${OUTPUT_TEST}"; then
  echo "Generated test is missing the calculator result assertion." >&2
  exit 1
fi
if ! grep -q 'keep_artifacts=True' "${OUTPUT_TEST}"; then
  echo "Generated test does not keep replay diagnostics on failure." >&2
  exit 1
fi

echo "Wrote ${OUTPUT_TEST}"
