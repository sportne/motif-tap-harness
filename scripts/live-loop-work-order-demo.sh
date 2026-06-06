#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop/work-order}"
REPLAY_DIR="${BASE_DIR}/replay"
GUI_TEST="${ROOT_DIR}/tests/gui/test_work_order_submit.py"
EXPECTED_RESULT=$'customer=Ada Lovelace\nservice=calibration\nrush=true\nquantity=3\nsubmitted_via=menu'

cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    shopt -s nullglob
    for dir in /tmp/motif-test-*; do
      cp -R "$dir" "${REPLAY_DIR}/" 2>/dev/null || true
    done
    shopt -u nullglob
    chmod -R u+rwX,go+rX "${REPLAY_DIR}" 2>/dev/null || true
    echo "Work-order live-loop demo failed. Artifacts are in ${BASE_DIR}" >&2
    for log in translate.log pytest.log xvfb-replay.log openbox-replay.log xdotool.log; do
      if [[ -s "${BASE_DIR}/${log}" || -s "${REPLAY_DIR}/${log}" ]]; then
        echo "===== ${log} =====" >&2
        tail -100 "${BASE_DIR}/${log}" "${REPLAY_DIR}/${log}" 2>/dev/null >&2 || true
      fi
    done
  fi
  kill "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  wait "${openbox_pid:-}" "${xvfb_pid:-}" 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT

mkdir -p "${BASE_DIR}"
rm -rf "${REPLAY_DIR}"
mkdir -p "${REPLAY_DIR}"

bash "${ROOT_DIR}/scripts/live-loop-work-order-translate.sh" >"${BASE_DIR}/translate.log"

for display_number in $(seq 99 109); do
  if [[ -e "/tmp/.X${display_number}-lock" ]]; then
    continue
  fi
  Xvfb ":${display_number}" -screen 0 1280x1024x24 >"${REPLAY_DIR}/xvfb-replay.log" 2>&1 &
  xvfb_pid=$!
  sleep 1
  if kill -0 "$xvfb_pid" 2>/dev/null; then
    export DISPLAY=":${display_number}"
    break
  fi
done

if [[ -z "${DISPLAY:-}" ]]; then
  echo "Could not start replay Xvfb on displays :99 through :109." >&2
  exit 1
fi

openbox >"${REPLAY_DIR}/openbox-replay.log" 2>&1 &
openbox_pid=$!
sleep 1

rm -rf /tmp/motif-work-order
export MOTIF_TAP_SO="${ROOT_DIR}/c/libxttap.so"
export MOTIF_TAP_XDOTOOL_LOG="${REPLAY_DIR}/xdotool.log"
export TMPDIR="/tmp"

pytest "${GUI_TEST}" -q | tee "${REPLAY_DIR}/pytest.log"

test "$(cat /tmp/motif-work-order/result.txt)" = "${EXPECTED_RESULT}"
echo "Work-order live-loop demo passed."
