#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/flash-boot
cross="${CROSS_COMPILE:-riscv64-linux-gnu-}"
"${cross}gcc" -march=rv64imac_zicsr_zifencei -mabi=lp64 -mcmodel=medany \
  -Os -ffreestanding -fno-builtin -fno-pic -fno-stack-protector -msmall-data-limit=0 \
  -nostdlib -static -Wl,--build-id=none -Wl,-T,boot/flash.ld \
  boot/flash_start.S boot/flash_boot.c -o build/flash-boot/boot.elf
"${cross}objcopy" -O binary build/flash-boot/boot.elf build/flash-boot/boot.bin
"${cross}objdump" -d build/flash-boot/boot.elf > build/flash-boot/boot.dis
"${cross}size" build/flash-boot/boot.elf
