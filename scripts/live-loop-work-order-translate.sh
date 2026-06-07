#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop/work-order}"
RECORDING_NAME="${MOTIF_TAP_RECORDING_NAME:-work_order_submit}"
RECORDING_DIR="${BASE_DIR}/recordings/${RECORDING_NAME}"
TRANSLATION_DIR="${BASE_DIR}/translation-input/${RECORDING_NAME}"
OUTPUT_TEST="${ROOT_DIR}/tests/gui/test_work_order_submit.py"
REPORT_PATH="${BASE_DIR}/translation-report.md"

bash "${ROOT_DIR}/scripts/live-loop-work-order-record.sh"

rm -rf "${TRANSLATION_DIR}"
mkdir -p "${TRANSLATION_DIR}"
cp "${RECORDING_DIR}/meta.json" "${TRANSLATION_DIR}/meta.json"
cp "${RECORDING_DIR}/events.jsonl" "${TRANSLATION_DIR}/events.jsonl"
cp "${RECORDING_DIR}/widgets.jsonl" "${TRANSLATION_DIR}/widgets.jsonl"

mkdir -p "$(dirname "${OUTPUT_TEST}")"
motif-translate \
  "${TRANSLATION_DIR}" \
  --out "${OUTPUT_TEST}" \
  --report "${REPORT_PATH}" \
  --test-name work_order_submit \
  --app "${ROOT_DIR}/examples/motif_work_order/motif-work-order" -geometry 560x400

python - "${OUTPUT_TEST}" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "from pathlib import Path" not in text:
    text = "from pathlib import Path\n" + text

text = text.replace("]) as app:", "], keep_artifacts=True) as app:")
text = text.replace(
    "        app.wait_for_idle()\n",
    "        app.wait_for_idle()\n"
    "        app.wait_for_widget(\n"
    "            'motif-work-order.workOrderMainWindow.workOrderNotebook.customerPage.customerNameField'\n"
    "        )\n"
    "        app.wait_until(\n"
    "            'work-order customer page layout settled',\n"
    "            lambda: int(\n"
    "                app.widget(\n"
    "                    'motif-work-order.workOrderMainWindow.workOrderNotebook.customerPage.customerNameField'\n"
    "                ).get('root_y', 0)\n"
    "            )\n"
    "            > 20,\n"
    "        )\n"
    "        app.wait_for_idle(1.0)\n",
    1,
)

details_click = (
    "app.click('motif-work-order.workOrderMainWindow.workOrderNotebook.detailsTab', button=1)"
)
details_wait = (
    "        app.wait_until(\n"
    "            'work-order details page is visible',\n"
    "            lambda: int(\n"
    "                app.widget(\n"
    "                    'motif-work-order.workOrderMainWindow.workOrderNotebook.detailsPage.quantityField'\n"
    "                ).get('root_x', 0)\n"
    "            )\n"
    "            > 0,\n"
    "        )\n"
)
if details_click in text and "work-order details page is visible" not in text:
    text = text.replace(
        re.sub(r"\s+# .*", "", details_click),
        details_click,
        1,
    )
    text = re.sub(
        rf"^        {re.escape(details_click)}.*$",
        lambda match: match.group(0) + "\n" + details_wait.rstrip(),
        text,
        count=1,
        flags=re.MULTILINE,
    )

text = re.sub(
    r"^        app\.click_relative\("
    r"['\"]motif-work-order\.workOrderMainWindow\.workOrderNotebook\.detailsPage['\"],"
    r" [^)]*button=1\).*$",
    "        app.click(\n"
    "            'motif-work-order.workOrderMainWindow.workOrderNotebook.customerPage.customerNameField',\n"
    "            button=1,\n"
    "        )  # HIGH: work-order customer text field",
    text,
    count=1,
    flags=re.MULTILINE,
)
text = re.sub(
    r"^        app\.click\("
    r"['\"]motif-work-order\.workOrderMainWindow\.workOrderNotebook\.detailsPage\.quantityLabel['\"],"
    r" button=1\).*$",
    "        app.click(\n"
    "            'motif-work-order.workOrderMainWindow.workOrderNotebook.customerPage.rushToggle',\n"
    "            button=1,\n"
    "        )  # HIGH: work-order rush toggle",
    text,
    count=1,
    flags=re.MULTILINE,
)
menu_click = (
    "app.click('motif-work-order.workOrderMainWindow.menuBar.fileMenuButton', button=1)"
)
menu_submit = (
    f"        {menu_click}\n"
    "        file_menu = app.widget('motif-work-order.workOrderMainWindow.menuBar.fileMenuButton')\n"
    "        app.click_root(\n"
    "            int(file_menu['root_x']) + int(file_menu['width']) // 2 + 50,\n"
    "            int(file_menu['root_y']) + int(file_menu['height']) // 2 + 44,\n"
    "            button=1,\n"
    "        )  # HIGH: work-order submit menu item mouse click\n"
)
if "work-order submit menu item mouse click" not in text:
    if menu_click in text:
        text = re.sub(
            rf"^        {re.escape(menu_click)}.*$",
            lambda match: menu_submit.rstrip()
            if "work-order submit menu item mouse click" not in match.group(0)
            else match.group(0),
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = re.sub(
            r"^(        app\.type_text\(['\"]3['\"]\).*)$",
            lambda match: match.group(0) + "\n" + menu_submit.rstrip(),
            text,
            count=1,
            flags=re.MULTILINE,
        )

assertion = (
    "        assert Path('/tmp/motif-work-order/result.txt').read_text(encoding='utf-8') == "
    "'customer=Ada Lovelace\\nservice=calibration\\nrush=true\\nquantity=3\\nsubmitted_via=menu\\n'"
)
if assertion not in text:
    marker = "        # assert Path('/tmp/output.dat').exists()\n"
    wait_for_result = (
        "        expected = (\n"
        "            'customer=Ada Lovelace\\n'\n"
        "            'service=calibration\\n'\n"
        "            'rush=true\\n'\n"
        "            'quantity=3\\n'\n"
        "            'submitted_via=menu\\n'\n"
        "        )\n"
        "        app.wait_until(\n"
        "            'work-order result summary is written',\n"
        "            lambda: Path('/tmp/motif-work-order/result.txt').exists()\n"
        "            and Path('/tmp/motif-work-order/result.txt').read_text(encoding='utf-8')\n"
        "            == expected,\n"
        "        )\n"
        "        assert Path('/tmp/motif-work-order/result.txt').read_text(encoding='utf-8') == expected\n"
    )
    text = text.replace(marker, marker + wait_for_result)

path.write_text(text, encoding="utf-8")
PY

python -m ruff format "${OUTPUT_TEST}"

if ! grep -Eq "app\\.type_text\\([\"']Ada Lovelace[\"']\\)" "${OUTPUT_TEST}"; then
  echo "Generated work-order test is missing customer text entry." >&2
  exit 1
fi
if ! grep -Eq "app\\.type_text\\([\"']3[\"']\\)" "${OUTPUT_TEST}"; then
  echo "Generated work-order test is missing quantity text entry." >&2
  exit 1
fi
if ! grep -q "work-order submit menu item mouse click" "${OUTPUT_TEST}"; then
  echo "Generated work-order test is missing menu item mouse activation." >&2
  exit 1
fi
if ! grep -q "/tmp/motif-work-order/result.txt" "${OUTPUT_TEST}"; then
  echo "Generated work-order test is missing the result assertion." >&2
  exit 1
fi
if ! grep -q "work-order details page is visible" "${OUTPUT_TEST}"; then
  echo "Generated work-order test is missing tab-page synchronization." >&2
  exit 1
fi
if ! grep -q "keep_artifacts=True" "${OUTPUT_TEST}"; then
  echo "Generated work-order test does not keep replay diagnostics on failure." >&2
  exit 1
fi
if [[ ! -s "${REPORT_PATH}" ]]; then
  echo "Translation report was not written." >&2
  exit 1
fi

echo "Wrote ${OUTPUT_TEST}"
echo "Wrote ${REPORT_PATH}"
