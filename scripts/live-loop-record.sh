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
  --app "${ROOT_DIR}/examples/motif_calc/motif-calc" \
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
deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    if state_path.exists() and state_path.stat().st_size:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        paths = {widget["path"] for widget in state.get("widgets", [])}
        if all(any(path.endswith(suffix) for path in paths) for suffix in required):
            raise SystemExit(0)
    time.sleep(0.1)
raise SystemExit("required calculator widgets did not appear")
PY

python - "${RECORDING_DIR}/latest-state.json" <<'PY' >"${BASE_DIR}/clicks.env"
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
widgets = state.get("widgets", [])

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
for point in DIGIT7 MULTIPLY DIGIT6 EQUALS; do
  if ! kill -0 "$record_pid" 2>/dev/null; then
    echo "motif-record exited before scripted clicks completed." >&2
    exit 1
  fi
  x_var="${point}_X"
  y_var="${point}_Y"
  x="${!x_var}"
  y="${!y_var}"
  xdotool mousemove "$x" "$y" click 1
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

button_count="$(python - "${RECORDING_DIR}/events.jsonl" <<'PY'
import json
import sys
from pathlib import Path

count = 0
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.strip() and json.loads(line).get("kind") == "button":
        count += 1
print(count)
PY
)"
if [[ "$button_count" -le 0 ]]; then
  echo "Expected non-zero button events, got ${button_count}." >&2
  exit 1
fi

echo "RECORDING_DIR=${RECORDING_DIR}"
cat "${BASE_DIR}/normalize.log"
echo "button_events=${button_count}"
