#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tests/check_cpu_smoke.py
python3 tests/check_gemmini.py
python3 tests/check_loop_stress.py
python3 tests/check_dma_beat64.py
