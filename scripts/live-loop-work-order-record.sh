#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop/work-order}"
RECORDING_PARENT="${BASE_DIR}/recordings"
RECORDING_NAME="${MOTIF_TAP_RECORDING_NAME:-work_order_submit}"
RECORDING_DIR="${RECORDING_PARENT}/${RECORDING_NAME}"
EXPECTED_RESULT=$'customer=Ada Lovelace\nservice=calibration\nrush=true\nquantity=3\nsubmitted_via=menu'

cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    echo "Work-order recording failed. Artifacts are in ${BASE_DIR}" >&2
    for log in xvfb.log openbox.log motif-record.log normalize.log; do
      if [[ -s "${BASE_DIR}/${log}" ]]; then
        echo "===== ${log} =====" >&2
        tail -100 "${BASE_DIR}/${log}" >&2 || true
      fi
    done
  fi
  kill "${record_pid:-}" "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  wait "${record_pid:-}" "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT

rm -rf "${RECORDING_DIR}" /tmp/motif-work-order
mkdir -p "${RECORDING_PARENT}"

for display_number in $(seq 99 109); do
  if [[ -e "/tmp/.X${display_number}-lock" ]]; then
    continue
  fi
  Xvfb ":${display_number}" -screen 0 1280x1024x24 >"${BASE_DIR}/xvfb.log" 2>&1 &
  xvfb_pid=$!
  sleep 1
  if kill -0 "$xvfb_pid" 2>/dev/null; then
    export DISPLAY=":${display_number}"
    break
  fi
done

if [[ -z "${DISPLAY:-}" ]]; then
  echo "Could not start Xvfb on displays :99 through :109." >&2
  exit 1
fi

openbox >"${BASE_DIR}/openbox.log" 2>&1 &
openbox_pid=$!
sleep 1

motif-record \
  --name "${RECORDING_NAME}" \
  --output-dir "${RECORDING_PARENT}" \
  --tap-so "${ROOT_DIR}/c/libxttap.so" \
  --seconds 20 \
  --app "${ROOT_DIR}/examples/motif_work_order/motif-work-order" -geometry 560x400 \
  >"${BASE_DIR}/motif-record.log" 2>&1 &
record_pid=$!

deadline=$((SECONDS + 10))
while [[ $SECONDS -lt $deadline ]]; do
  if [[ -s "${RECORDING_DIR}/latest-state.json" ]]; then
    break
  fi
  if ! kill -0 "$record_pid" 2>/dev/null; then
    echo "motif-record exited before work-order state appeared." >&2
    exit 1
  fi
  sleep 0.1
done
if [[ ! -s "${RECORDING_DIR}/latest-state.json" ]]; then
  echo "motif-record did not produce work-order state before the readiness deadline." >&2
  exit 1
fi

python - "${RECORDING_DIR}/latest-state.json" <<'PY'
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
required = [
    ".customerNameField",
    ".rushToggle",
    ".detailsTab",
    ".fileMenuButton",
]
deadline = time.monotonic() + 15
while time.monotonic() < deadline:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        time.sleep(0.1)
        continue

    widgets = state.get("widgets", [])
    ready = True
    for suffix in required:
        matches = [widget for widget in widgets if widget["path"].endswith(suffix)]
        if not matches:
            ready = False
            break
        widget = matches[0]
        if (
            not widget.get("managed", True)
            or not widget.get("sensitive", True)
            or not widget.get("realized", True)
            or int(widget.get("width", 0)) <= 0
            or int(widget.get("height", 0)) <= 0
            or int(widget.get("root_y", 0)) <= 20
        ):
            ready = False
            break
    if ready:
        raise SystemExit(0)
    time.sleep(0.1)
raise SystemExit("required work-order customer widgets did not appear")
PY

python - "${RECORDING_DIR}/latest-state.json" <<'PY' >"${BASE_DIR}/customer-clicks.env"
import json
import sys
from pathlib import Path

widgets = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("widgets", [])


def emit(name, suffix):
    widget = next(widget for widget in widgets if widget["path"].endswith(suffix))
    x = int(widget["root_x"]) + int(widget["width"]) // 2
    y = int(widget["root_y"]) + int(widget["height"]) // 2
    print(f"{name}_X={x}")
    print(f"{name}_Y={y}")


for widget in widgets:
    if widget.get("window") and widget.get("class") != "XmDisplay":
        print(f"APP_WINDOW={widget['window']}")
        break

emit("CUSTOMER", ".customerNameField")
emit("RUSH", ".rushToggle")
emit("DETAILS_TAB", ".detailsTab")
PY

source "${BASE_DIR}/customer-clicks.env"
if [[ -n "${APP_WINDOW:-}" ]]; then
  xdotool windowactivate --sync "${APP_WINDOW}" || true
fi

xdotool mousemove "${CUSTOMER_X}" "${CUSTOMER_Y}"
sleep 0.05
xdotool click 1
sleep 0.2
xdotool type --delay 30 "Ada Lovelace"
sleep 0.2

xdotool mousemove "${RUSH_X}" "${RUSH_Y}"
sleep 0.05
xdotool click 1
sleep 0.2

xdotool mousemove "${DETAILS_TAB_X}" "${DETAILS_TAB_Y}"
sleep 0.05
xdotool click 1
sleep 0.5

python - "${RECORDING_DIR}/latest-state.json" <<'PY'
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
required = [".calibrationToggle", ".quantityField"]
deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        time.sleep(0.1)
        continue
    widgets = state.get("widgets", [])
    ready = True
    for suffix in required:
        matches = [widget for widget in widgets if widget["path"].endswith(suffix)]
        if not matches:
            ready = False
            break
        widget = matches[0]
        if int(widget.get("root_x", 0)) <= 0 or int(widget.get("root_y", 0)) <= 20:
            ready = False
            break
    if ready:
        raise SystemExit(0)
    time.sleep(0.1)
raise SystemExit("required work-order details widgets did not appear")
PY

python - "${RECORDING_DIR}/latest-state.json" <<'PY' >"${BASE_DIR}/details-clicks.env"
import json
import sys
from pathlib import Path

widgets = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("widgets", [])


def emit(name, suffix):
    widget = next(widget for widget in widgets if widget["path"].endswith(suffix))
    x = int(widget["root_x"]) + int(widget["width"]) // 2
    y = int(widget["root_y"]) + int(widget["height"]) // 2
    print(f"{name}_X={x}")
    print(f"{name}_Y={y}")


emit("CALIBRATION", ".calibrationToggle")
emit("QUANTITY", ".quantityField")
PY

source "${BASE_DIR}/details-clicks.env"

xdotool mousemove "${CALIBRATION_X}" "${CALIBRATION_Y}"
sleep 0.05
xdotool click 1
sleep 0.2

xdotool mousemove "${QUANTITY_X}" "${QUANTITY_Y}"
sleep 0.05
xdotool click 1
sleep 0.2
xdotool key 3
sleep 0.2

# Submit through the File menu item's accelerator. The action still invokes the
# Submit Work Order menu item callback, but avoids transient popup-shell input
# behavior that cnee does not record reliably.
xdotool key F9
sleep 0.5

python - "${EXPECTED_RESULT}" "${BASE_DIR}/recorded-result.txt" <<'PY'
import sys
import time
from pathlib import Path

expected = sys.argv[1]
artifact = Path(sys.argv[2])
result = Path("/tmp/motif-work-order/result.txt")
deadline = time.monotonic() + 5
while time.monotonic() < deadline:
    if result.exists():
        actual = result.read_text(encoding="utf-8")
        artifact.write_text(actual, encoding="utf-8")
        if actual.strip() == expected:
            raise SystemExit(0)
    time.sleep(0.1)
if result.exists():
    raise SystemExit(
        "work-order result file did not match expected summary:\n"
        + result.read_text(encoding="utf-8")
    )
raise SystemExit("work-order result file was not written")
PY

wait "$record_pid"

motif-normalize-xnee \
  "${RECORDING_DIR}/xnee-human.txt" \
  --out "${RECORDING_DIR}/events.jsonl" \
  --stats \
  >"${BASE_DIR}/normalize.log"

for file in meta.json xnee-human.txt events.jsonl widgets.jsonl latest-state.json; do
  test -s "${RECORDING_DIR}/${file}"
done

input_event_count="$(python - "${RECORDING_DIR}/events.jsonl" <<'PY'
import json
import sys
from pathlib import Path

count = 0
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.strip() and json.loads(line).get("kind") in {"button", "key"}:
        count += 1
print(count)
PY
)"
if [[ "$input_event_count" -le 0 ]]; then
  echo "Expected non-zero input events, got ${input_event_count}." >&2
  exit 1
fi

echo "RECORDING_DIR=${RECORDING_DIR}"
cat "${BASE_DIR}/normalize.log"
echo "input_events=${input_event_count}"
