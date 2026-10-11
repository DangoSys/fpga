#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare_sources.py "$@"
python3 scripts/resolve_config.py
sbt -batch 'runMain fpga.arty.linux.EmitToyLinux build/serial-raw --fpga-memories --serial-fpga' \
  'runMain fpga.arty.linux.EmitToyLinux build/serial-reference --serial-fpga' \
  'runMain fpga.arty.linux.EmitRoutingCheck build/routing-check'
python3 scripts/prepare_fpga_memories.py build/serial-raw/ToyLinuxChip.sv --output-dir build/serial-bound
python3 scripts/bind_fpu_rf.py
python3 scripts/export_capabilities.py
python3 scripts/verify_target.py --core
