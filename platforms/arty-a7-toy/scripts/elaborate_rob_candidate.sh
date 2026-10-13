#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare_sources.py "$@"
python3 scripts/resolve_config.py
python3 scripts/check_globalrob.py
sbt -Dfpga.robOperandRam=true -batch \
  'runMain fpga.arty.linux.EmitToyLinux build/serial-raw --fpga-memories --serial-fpga' \
  'runMain fpga.arty.linux.EmitToyLinux build/serial-reference --serial-fpga' \
  'runMain fpga.arty.linux.EmitRoutingCheck build/routing-check'
python3 scripts/prepare_rob_candidate.py \
  --baseline-memory-manifest "$(python3 scripts/history_paths.py 2026-10-11/MEMORY_MANIFEST.json)"
python3 scripts/export_capabilities.py
