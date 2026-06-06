#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop}"
RECORDING_PARENT="${BASE_DIR}/recordings"
RECORDING_NAME="${MOTIF_TAP_RECORDING_NAME:-calculator_multiply}"
RECORDING_DIR="${RECORDING_PARENT}/${RECORDING_NAME}"

cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    echo "Recording failed. Artifacts are in ${BASE_DIR}" >&2
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

rm -rf "${RECORDING_DIR}"
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
  --seconds 30 \
  --app "${ROOT_DIR}/examples/motif_calc/motif-calc" -geometry 400x320 \
  >"${BASE_DIR}/motif-record.log" 2>&1 &
record_pid=$!

deadline=$((SECONDS + 10))
while [[ $SECONDS -lt $deadline ]]; do
  if [[ -s "${RECORDING_DIR}/latest-state.json" ]]; then
    break
  fi
  if ! kill -0 "$record_pid" 2>/dev/null; then
    echo "motif-record exited before calculator state appeared." >&2
    exit 1
  fi
  sleep 0.1
done

python - "${RECORDING_DIR}/latest-state.json" <<'PY'
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
required = [".digit7", ".multiplyButton", ".digit6", ".equalsButton"]
deadline = time.monotonic() + 15
while time.monotonic() < deadline:
    try:
        if not state_path.stat().st_size:
            time.sleep(0.1)
            continue
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        time.sleep(0.1)
        continue

    widgets = state.get("widgets", [])
    ready = True
    centers = set()
    for suffix in required:
        matches = [widget for widget in widgets if widget["path"].endswith(suffix)]
        if not matches:
            ready = False
            break
        widget = matches[0]
        root_x = int(widget.get("root_x", 0))
        root_y = int(widget.get("root_y", 0))
        width = int(widget.get("width", 0))
        height = int(widget.get("height", 0))
        if (
            not widget.get("managed", True)
            or not widget.get("sensitive", True)
            or not widget.get("realized", True)
            or width <= 0
            or height <= 0
            or root_x <= 0
            or root_y <= 20
        ):
            ready = False
            break
        centers.add((root_x + width // 2, root_y + height // 2))
    if len(centers) != len(required):
        ready = False
    if ready:
        raise SystemExit(0)
    time.sleep(0.1)
raise SystemExit("required calculator widgets did not appear")
PY

python - "${RECORDING_DIR}/latest-state.json" "${RECORDING_DIR}/translation-widgets.jsonl" <<'PY'
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
deadline = time.monotonic() + 5
while True:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        break
    except (FileNotFoundError, json.JSONDecodeError):
        if time.monotonic() >= deadline:
            raise
        time.sleep(0.05)
Path(sys.argv[2]).write_text(json.dumps(state, separators=(",", ":")) + "\n", encoding="utf-8")
PY

python - "${RECORDING_DIR}/latest-state.json" <<'PY' >"${BASE_DIR}/clicks.env"
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
deadline = time.monotonic() + 5
while True:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        break
    except (FileNotFoundError, json.JSONDecodeError):
        if time.monotonic() >= deadline:
            raise
        time.sleep(0.05)
widgets = state.get("widgets", [])
for widget in widgets:
    if widget.get("window") and widget.get("class") != "XmDisplay":
        print(f"APP_WINDOW={widget['window']}")
        break

for key, suffix in [
    ("DIGIT7", ".digit7"),
    ("MULTIPLY", ".multiplyButton"),
    ("DIGIT6", ".digit6"),
    ("EQUALS", ".equalsButton"),
]:
    widget = next(w for w in widgets if w["path"].endswith(suffix))
    x = int(widget["root_x"]) + int(widget["width"]) // 2
    y = int(widget["root_y"]) + int(widget["height"]) // 2
    print(f"{key}_X={x}")
    print(f"{key}_Y={y}")
PY

source "${BASE_DIR}/clicks.env"
sleep 1
if [[ -n "${APP_WINDOW:-}" ]]; then
  xdotool windowactivate --sync "${APP_WINDOW}" || true
fi
for point in DIGIT7 MULTIPLY DIGIT6 EQUALS; do
  if ! kill -0 "$record_pid" 2>/dev/null; then
    echo "motif-record exited before scripted input completed." >&2
    exit 1
  fi
  x_var="${point}_X"
  y_var="${point}_Y"
  xdotool mousemove "${!x_var}" "${!y_var}"
  sleep 0.05
  xdotool click 1
  sleep 0.2
done

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
