"""Run alternating OS/WS multi-tile loops across internal mesh-tag wrap."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "build/loop-stress"
out.mkdir(parents=True, exist_ok=True)
library = ROOT / "tests/reference/bb-tests/workloads/lib"
workloads = ROOT / "tests/reference/examples/balls/gemmini/workloads"
elf = out / "stress.elf"
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
        "-I",
        str(workloads),
        "-nostdlib",
        "-nostartfiles",
        "-Wl,--no-relax,--gc-sections",
        "-T",
        str(ROOT / "tests/cpu_smoke.ld"),
        str(ROOT / "tests/gemmini_start.S"),
        str(ROOT / "tests/serial_loop_stress.c"),
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
        "whole Toy 40 alternating multi tile OS WS loops",
    ],
    check=True,
)
