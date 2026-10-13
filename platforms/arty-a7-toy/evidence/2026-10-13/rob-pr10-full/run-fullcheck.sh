#!/usr/bin/env bash
set -euo pipefail
source scripts/toolchain.sh
mkdir -p build/fullcheck
phase() { printf '%s
' "$1" >build/fullcheck/phase.txt; printf 'FULLCHECK_PHASE %s
' "$1"; }
phase INPUTS
python3 build/bootstrap.py
python3 scripts/verify_target.py
python3 scripts/verify_rob_evidence.py
python3 scripts/verify_pr10_evidence.py
phase ELABORATE
timeout --signal=TERM --kill-after=15s 3600s bash scripts/elaborate_rob_candidate.sh --repository build/baseline.git
python3 scripts/verify_rob_evidence.py --core
phase OFFLINE_INTERFACES
python3 scripts/check_board.py
python3 scripts/check_programming_scripts.py
python3 scripts/check_flash_guards.py
python3 scripts/check_runner_status.py
python3 scripts/check_platform_mutations.py
phase MEMORY_AND_UNITS
timeout --signal=TERM --kill-after=15s 3600s python3 tests/check_fpga_memories.py --original build/serial-reference/ToyLinuxChip.sv --bound build/serial-bound
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/check_core_units.py
python3 tests/check_routing.py
phase WHOLE_CHIP
timeout --signal=TERM --kill-after=15s 3600s bash scripts/build_test_programs.sh
timeout --signal=TERM --kill-after=15s 3600s python3 tests/check_ws_round.py
timeout --signal=TERM --kill-after=15s 3600s python3 tests/check_ws_shift_edges.py
timeout --signal=TERM --kill-after=15s 3600s python3 tests/check_fpu_shared.py --baseline-core ../reference-fpu
phase BOARD_REGRESSION
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/run_board_regression.py
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/check_board_uart_boot.py
phase BOARD_IMPLEMENTATION
python3 scripts/start_rob_board_build.py >build/fullcheck/BOARD_LAUNCH.json
phase LINUX_RTL
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/check_board_linux.py
phase WAIT_BOARD
python3 - <<'PYCHECK'
import json,time
from pathlib import Path
launch=json.loads(Path('build/fullcheck/BOARD_LAUNCH.json').read_text());record=Path(launch['output_directory'])/'RUN.json'
started=time.monotonic()
while True:
    data=json.loads(record.read_text())
    if data['status'] not in ['CREATED','RUNNING']:break
    if time.monotonic()-started>3615:raise TimeoutError('Bounded board completion wait')
    time.sleep(10)
assert data['status']=='COMPLETED' and data['exit_code']==0 and data['bitstream_generated'],data
assert data['candidate_core_unchanged'] and data['candidate_memory_unchanged'],data
print('PASS full board implementation',launch['output_directory'])
PYCHECK
phase REAL_XILINX_CDC
board_run=$(python3 -c 'import json,pathlib;print(pathlib.Path(json.load(open("build/fullcheck/BOARD_LAUNCH.json"))["output_directory"]).name)')
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/check_board_cdc.py "$board_run"
phase COMPLETE
printf 'PASS ROB_PR10_FULL_VALIDATION
'
