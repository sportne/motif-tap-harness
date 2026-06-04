#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop/hook-smoke}"

cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    echo "Hook smoke failed. Artifacts are in ${ARTIFACT_DIR}" >&2
    for log in xvfb.log openbox.log calculator.log inspect-state.txt; do
      if [[ -s "${ARTIFACT_DIR}/${log}" ]]; then
        echo "===== ${log} =====" >&2
        tail -100 "${ARTIFACT_DIR}/${log}" >&2 || true
      fi
    done
  fi
  kill "${calc_pid:-}" "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  wait "${calc_pid:-}" "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT

rm -rf "${ARTIFACT_DIR}"
mkdir -p "${ARTIFACT_DIR}"

for display_number in $(seq 99 109); do
  if [[ -e "/tmp/.X${display_number}-lock" ]]; then
    continue
  fi
  Xvfb ":${display_number}" -screen 0 1280x1024x24 >"${ARTIFACT_DIR}/xvfb.log" 2>&1 &
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
sleep 1

openbox >"${ARTIFACT_DIR}/openbox.log" 2>&1 &
openbox_pid=$!
sleep 1

export MOTIF_TAP_STATE="${ARTIFACT_DIR}/latest-state.json"
export MOTIF_TAP_LOG="${ARTIFACT_DIR}/widgets.jsonl"
export LD_PRELOAD="${ROOT_DIR}/c/libxttap.so${LD_PRELOAD:+:${LD_PRELOAD}}"

"${ROOT_DIR}/examples/motif_calc/motif-calc" >"${ARTIFACT_DIR}/calculator.log" 2>&1 &
calc_pid=$!

wait_for_required_widgets() {
  python - "$MOTIF_TAP_STATE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists() or path.stat().st_size == 0:
    raise SystemExit(1)

state = json.loads(path.read_text(encoding="utf-8"))
paths = {widget["path"] for widget in state.get("widgets", [])}
required_suffixes = [
    ".displayLabel",
    ".digit0",
    ".digit1",
    ".digit2",
    ".digit3",
    ".digit4",
    ".digit5",
    ".digit6",
    ".digit7",
    ".digit8",
    ".digit9",
    ".addButton",
    ".subtractButton",
    ".multiplyButton",
    ".divideButton",
    ".equalsButton",
    ".clearButton",
]
missing = [
    suffix
    for suffix in required_suffixes
    if not any(path.endswith(suffix) for path in paths)
]
if missing:
    raise SystemExit(1)
PY
}

deadline=$((SECONDS + 10))
while [[ $SECONDS -lt $deadline ]]; do
  if wait_for_required_widgets; then
    break
  fi
  if ! kill -0 "$calc_pid" 2>/dev/null; then
    echo "Calculator exited before hook state appeared." >&2
    exit 1
  fi
  sleep 0.1
done

test -s "${MOTIF_TAP_STATE}"
test -s "${MOTIF_TAP_LOG}"

if ! wait_for_required_widgets; then
  motif-inspect-state "${MOTIF_TAP_STATE}" >"${ARTIFACT_DIR}/inspect-state.txt" || true
  cat "${ARTIFACT_DIR}/inspect-state.txt" >&2 || true
  echo "Required calculator widgets did not appear in hook state." >&2
  exit 1
fi

motif-inspect-state "${MOTIF_TAP_STATE}" >"${ARTIFACT_DIR}/inspect-state.txt"
cat "${ARTIFACT_DIR}/inspect-state.txt"

echo "Hook smoke passed. Artifacts are in ${ARTIFACT_DIR}"
