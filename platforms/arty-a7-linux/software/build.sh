#!/usr/bin/env bash
# Build a real OpenSBI + Linux + BusyBox payload. Operator regression binaries
# still need to be installed before full Pebble acceptance can be claimed.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 software/prepare_platform.py
python3 software/prepare_dependencies.py
mkdir -p build/software/bb-tests/output/workloads
riscv64-unknown-linux-gnu-gcc -O2 -Wall -Wextra -Werror -ffp-contract=off \
  -march=rv64gc -mabi=lp64d -static software/linux_system_check.c -lm \
  -o build/software/bb-tests/output/workloads/linux_system_check-linux
cmake -S build/software/bb-tests/workloads/lib/kernel \
  -B build/software/kernel-build \
  -DBUCKYBALL_VISIBLE_HART_COUNT=1 -DBUCKYBALL_TOTAL_HART_COUNT=1 \
  -DBUCKYBALL_KERNEL_INTERACTIVE=ON
cmake --build build/software/kernel-build --target kernel-build
