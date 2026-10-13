"""Check unaligned and strided DMA round trips, with guards and page crossings."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "build/dma-beat64"
out.mkdir(parents=True, exist_ok=True)
library = ROOT / "tests/reference/bb-tests/workloads/lib"
elf = out / "dma.elf"
subprocess.run(
    [
        "riscv64-unknown-elf-gcc",
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-ffunction-sections",
        "-fdata-sections",
        "-msmall-data-limit=0",
        "-mcmodel=medany",
        "-march=rv64imafdc_zicsr_zifencei_zfh",
        "-mabi=lp64d",
        "-I",
        str(ROOT / "build/software"),
        "-I",
        str(library),
        "-nostdlib",
        "-nostartfiles",
        "-Wl,--no-relax,--gc-sections",
        "-T",
        str(ROOT / "tests/cpu_smoke.ld"),
        str(ROOT / "tests/gemmini_start.S"),
        str(ROOT / "tests/dma_beat64.c"),
        str(ROOT / "tests/gemmini_runtime.c"),
        str(library / "buckyball.c"),
        "-lgcc",
        "-o",
        str(elf),
    ],
    check=True,
)
subprocess.run(
    [
        sys.executable,
        str(ROOT / "tests/check_cpu_smoke.py"),
        "--program-elf",
        str(elf),
        "--output-dir",
        str(out / "simulation"),
        "--label",
        "whole Toy unaligned DMA 64 bit beats",
    ],
    check=True,
)
