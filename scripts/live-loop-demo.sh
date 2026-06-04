#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${MOTIF_TAP_LIVE_ARTIFACT_DIR:-/tmp/motif-tap-live-loop}"
REPLAY_DIR="${BASE_DIR}/replay"
GUI_TEST="${ROOT_DIR}/tests/gui/test_calculator_multiply.py"

cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    echo "Live-loop demo failed. Artifacts are in ${BASE_DIR}" >&2
    for log in translate.log pytest.log xvfb-replay.log openbox-replay.log; do
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

rm -rf "${REPLAY_DIR}"
mkdir -p "${REPLAY_DIR}"

"${ROOT_DIR}/scripts/live-loop-translate.sh" >"${BASE_DIR}/translate.log"

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

rm -f /tmp/motif-calc/result.txt
export MOTIF_TAP_SO="${ROOT_DIR}/c/libxttap.so"

pytest "${GUI_TEST}" -q | tee "${REPLAY_DIR}/pytest.log"

test "$(cat /tmp/motif-calc/result.txt)" = "42"
echo "Live-loop demo passed."
