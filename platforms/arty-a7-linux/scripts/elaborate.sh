#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare_sources.py "$@"
python3 scripts/resolve_config.py
export COURSIER_REPOSITORIES=https://repo.maven.apache.org/maven2
sbt -Dsbt.override.build.repos=true -Dsbt.repository.config=project/repositories \
  -batch 'runMain fpga.arty.linux.EmitPebbleLinux generated'
python3 scripts/prepare_rtl.py
python3 scripts/audit_sources.py
python3 scripts/audit_elaboration.py
