#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop}"
RECORDING_DIR="${BASE_DIR}/recordings/${MOTIF_TAP_RECORDING_NAME:-calculator_multiply}"
TRANSLATION_DIR="${BASE_DIR}/translation-input/${MOTIF_TAP_RECORDING_NAME:-calculator_multiply}"
OUTPUT_TEST="${ROOT_DIR}/tests/gui/test_calculator_multiply.py"

bash "${ROOT_DIR}/scripts/live-loop-record.sh"

rm -rf "${TRANSLATION_DIR}"
mkdir -p "${TRANSLATION_DIR}"
cp "${RECORDING_DIR}/meta.json" "${TRANSLATION_DIR}/meta.json"
cp "${RECORDING_DIR}/events.jsonl" "${TRANSLATION_DIR}/events.jsonl"
cp "${RECORDING_DIR}/translation-widgets.jsonl" "${TRANSLATION_DIR}/widgets.jsonl"

mkdir -p "$(dirname "${OUTPUT_TEST}")"
motif-translate \
  "${TRANSLATION_DIR}" \
  --out "${OUTPUT_TEST}" \
  --test-name calculator_multiply \
  --app "${ROOT_DIR}/examples/motif_calc/motif-calc" -geometry 400x320

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
    wait_for_result = (
        "        app.wait_until(\n"
        "            'calculator result is 42',\n"
        "            lambda: Path('/tmp/motif-calc/result.txt').exists()\n"
        "            and Path('/tmp/motif-calc/result.txt').read_text(encoding='utf-8').strip() == '42',\n"
        "        )\n"
    )
    text = text.replace(marker, marker + wait_for_result + assertion + "\n")

text = text.replace("]) as app:", "], keep_artifacts=True) as app:")
text = text.replace(
    "        app.wait_for_idle()\n",
    "        app.wait_for_idle()\n"
    "        app.wait_for_widget('motif-calc.calculatorForm.keypad.digit7')\n",
)
text = text.replace(
    "        app.wait_for_widget('motif-calc.calculatorForm.keypad.digit7')\n",
    "        app.wait_for_widget('motif-calc.calculatorForm.keypad.digit7')\n"
    "        app.wait_until(\n"
    "            'calculator layout settled',\n"
    "            lambda: int(app.widget('motif-calc.calculatorForm.keypad.digit7').get('root_y', 0)) > 20,\n"
    "        )\n"
    "        app.wait_for_idle(1.0)\n",
)
for widget_path, x, y in [
    ("motif-calc.calculatorForm.keypad.digit7", 9, 12),
    ("motif-calc.calculatorForm.keypad.multiplyButton", 9, 12),
    ("motif-calc.calculatorForm.keypad.digit6", 9, 12),
    ("motif-calc.calculatorForm.keypad.equalsButton", 10, 12),
]:
    text = text.replace(
        f"app.click({widget_path!r}, button=1)",
        f"app.click_relative({widget_path!r}, {x}, {y}, button=1)",
    )

path.write_text(text, encoding="utf-8")
PY

python -m ruff format "${OUTPUT_TEST}"

if ! grep -Eq "app\\.(click|press|type_text)" "${OUTPUT_TEST}"; then
  echo "Generated test is missing replay input actions." >&2
  exit 1
fi
if ! grep -q '/tmp/motif-calc/result.txt' "${OUTPUT_TEST}"; then
  echo "Generated test is missing the calculator result assertion." >&2
  exit 1
fi
if ! grep -q "calculator result is 42" "${OUTPUT_TEST}"; then
  echo "Generated test is missing calculator result synchronization." >&2
  exit 1
fi
if ! grep -q 'keep_artifacts=True' "${OUTPUT_TEST}"; then
  echo "Generated test does not keep replay diagnostics on failure." >&2
  exit 1
fi
if ! grep -Eq "app.wait_for_widget\\(['\"]motif-calc\\.calculatorForm\\.keypad\\.digit7['\"]\\)" "${OUTPUT_TEST}"; then
  echo "Generated test is missing calculator readiness synchronization." >&2
  exit 1
fi
if ! grep -q "calculator layout settled" "${OUTPUT_TEST}"; then
  echo "Generated test is missing calculator layout synchronization." >&2
  exit 1
fi
if ! grep -q "app.click_relative" "${OUTPUT_TEST}"; then
  echo "Generated test is missing recorded relative click positions." >&2
  exit 1
fi

echo "Wrote ${OUTPUT_TEST}"
