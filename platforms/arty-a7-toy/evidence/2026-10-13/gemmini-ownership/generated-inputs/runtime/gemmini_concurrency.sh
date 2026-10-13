#!/bin/sh
# BusyBox ash entry. One case per clean FPGA reset + Linux image load.
# Never delete /tmp/buckyball-gemmini.lock as a recovery operation.
set -u
mode=${1:-same}
case "$mode" in same|mixed|cpu|kill) ;; *) echo 'usage: sh gemmini_concurrency.sh same|mixed|cpu|kill'; exit 2 ;; esac
base=$(CDPATH= cd -- "$(busybox dirname -- "$0")" && pwd)
first="$base/gemmini_linux_check-linux"
second="$first"
if [ "$mode" = mixed ]; then
  first="$base/gemmini_os_cisc_basic_test-linux"
  second="$base/gemmini_ws_risc_basic_test-linux"
fi
for program in "$first" "$second"; do
  [ -x "$program" ] || { echo "MISSING $program"; exit 2; }
done
lock=/tmp/buckyball-gemmini.lock
if [ -e "$lock" ]; then
  state=$(cat "$lock")
  [ "$state" = 'BBGM1 CLEAN' ] || { echo 'DIRTY: reset FPGA/Linux; do not remove lock'; exit 76; }
fi
dir="/tmp/gemmini-ownership-$mode-$$"
mkdir "$dir" || exit 2
echo "OWNERSHIP_CASE START mode=$mode logs=$dir"
busybox sha256sum "$first" "$second" > "$dir/binaries.sha256"
cat /proc/uptime > "$dir/start.uptime"
p1= p2= hog= watcher=
watchdog() {
  limit=$1; shift
  sleep "$limit" & timer=$!
  trap 'kill "$timer" 2>/dev/null || :; wait "$timer" 2>/dev/null || :; exit 0' INT TERM
  wait "$timer" || return
  echo TIMEOUT > "$dir/timeout"
  for victim in "$@"; do kill -KILL "$victim" 2>/dev/null || :; done
}
cleanup() {
  for pid in "$p1" "$p2" "$hog"; do
    if [ -n "$pid" ]; then kill -KILL "$pid" 2>/dev/null || :; fi
  done
  if [ -n "$watcher" ]; then kill -TERM "$watcher" 2>/dev/null || :; fi
}
trap 'cleanup; exit 130' INT TERM
(while [ ! -f "$dir/go" ]; do sleep 1; done; exec "$first") > "$dir/a.log" 2>&1 &
p1=$!
if [ "$mode" != kill ]; then
  (while [ ! -f "$dir/go" ]; do sleep 1; done; exec "$second") > "$dir/b.log" 2>&1 &
  p2=$!
fi
if [ "$mode" = cpu ]; then
  (n=0; while :; do n=$((n + 1)); done) &
  hog=$!
fi
printf '%s %s\n' "$p1" "$p2" > "$dir/pids"
watchdog 180 "$p1" ${p2:+"$p2"} >/dev/null 2>&1 &
watcher=$!
busybox touch "$dir/go"
if [ "$mode" = kill ]; then
  # Stop a known live owner, then recheck the marker before SIGKILL. The exact
  # DMA phase is not claimed. Completion racing this probe is INCONCLUSIVE.
  count=0
  while [ "$count" -lt 60 ]; do
    if [ -f "$lock" ] && [ "$(cat "$lock")" = "BBGM1 DIRTY pid=$p1" ]; then break; fi
    kill -0 "$p1" 2>/dev/null || break
    sleep 1
    count=$((count + 1))
  done
  kill -STOP "$p1" 2>/dev/null || :
  sleep 1
  if [ ! -r "/proc/$p1/status" ] ||
     ! busybox grep -q '^State:.*T' "/proc/$p1/status" ||
     [ "$(cat "$lock" 2>/dev/null)" != "BBGM1 DIRTY pid=$p1" ]; then
    cleanup
    wait "$p1" 2>/dev/null || :
    echo 'OWNERSHIP_CASE INCONCLUSIVE: owner completed or could not be stopped; reset before retry'
    exit 77
  fi
  kill -KILL "$p1"
  wait "$p1"; a=$?
  p1=
  kill -TERM "$watcher" 2>/dev/null || :
  wait "$watcher" 2>/dev/null || :
  watcher=
  "$second" > "$dir/b.log" 2>&1 &
  p2=$!
  watchdog 10 "$p2" >/dev/null 2>&1 &
  watcher=$!
  wait "$p2"; b=$?; p2=
  cleanup
  wait "$watcher" 2>/dev/null || :
  watcher=
  printf '%s %s\n' "$a" "$b" > "$dir/returns"
  if [ "$a" -ne 137 ] || [ "$b" -ne 76 ] || [ -e "$dir/timeout" ] ||
     busybox grep -q 'GEMMINI_LEASE acquired' "$dir/b.log"; then
    echo "OWNERSHIP_CASE FAIL kill rc=$a next=$b"; exit 1
  fi
  echo 'OWNERSHIP_CASE PASS kill: next task rejected; full FPGA/Linux reset required'
else
  wait "$p1"; a=$?; p1=
  wait "$p2"; b=$?; p2=
  cleanup
  wait "$watcher" 2>/dev/null || :
  if [ -n "$hog" ]; then wait "$hog" 2>/dev/null || :; fi
  printf '%s %s\n' "$a" "$b" > "$dir/returns"
  cat /proc/uptime > "$dir/end.uptime"
  if [ "$a" -ne 0 ] || [ "$b" -ne 0 ] || [ -e "$dir/timeout" ] ||
     [ "$(cat "$lock")" != 'BBGM1 CLEAN' ]; then
    echo "OWNERSHIP_CASE FAIL mode=$mode rc=$a,$b"; exit 1
  fi
  for log in "$dir/a.log" "$dir/b.log"; do
    if [ "$(busybox grep -c '^GEMMINI_LEASE complete$' "$log")" != 1 ]; then
      echo "OWNERSHIP_CASE FAIL missing completion in $log"; exit 1
    fi
  done
  echo "OWNERSHIP_CASE PASS mode=$mode results_correct=1 both_completed=1 shell_responsive=1"
fi
