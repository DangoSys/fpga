"""Run pinned upstream Gemmini C tests on the complete emitted chip."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", type=Path, default=ROOT / "build/serial-bound")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build/gemmini-tests")
    parser.add_argument("--cases", nargs="+")
    parser.add_argument("--diagnostic", action="store_true")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    reference = ROOT / "tests/reference"
    manifest = json.loads((ROOT / "tests/REFERENCE_MANIFEST.json").read_text())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((reference / name).read_bytes()).hexdigest() == expected
    library = reference / "bb-tests/workloads/lib"
    workloads = reference / "examples/balls/gemmini/workloads"
    config = json.loads((ROOT / "build/original-toy.json").read_text())
    entries = config["accelerator"]["ballDomain"]["ballISA"]
    (out / "ballISA.h").write_text(
        "// Retained Gemmini encodings, unchanged from upstream.\n"
        + "\n".join(
            f"#define BB_FUNC7_{e['mnemonic']} {e['funct7']}"
            for e in entries
            if e["bid"] == 0
        )
        + "\n"
    )
    (out / "params.h").write_text(
        "#define BANK_WIDTH 64\n#define VIRTUAL_BANK_NUM 16\n"
    )
    sources = sorted((workloads / "ctests").glob("*.c"))
    if args.cases:
        sources = [p for p in sources if p.stem in args.cases]
        assert {p.stem for p in sources} == set(args.cases)
    adapted = out / "dimension-8-sources"
    adapted.mkdir(exist_ok=True)
    adapted_sources = []
    for source in sources:
        text = source.read_text()
        assert "#define DIM 16" in text, source
        target = adapted / source.name
        target.write_text(text.replace("#define DIM 16", "#define DIM 8"))
        adapted_sources.append(target)
    sources = adapted_sources
    common = [
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
        str(out),
        "-I",
        str(library),
        "-I",
        str(workloads),
    ]
    objects = []
    for i, source in enumerate(sources, 1):
        obj = out / f"case_{i}.o"
        subprocess.run(
            common + [f"-Dmain=case_{i}", "-c", str(source), "-o", str(obj)], check=True
        )
        objects.append(obj)
    runner = out / "runner.c"
    lines = ["#include <stdint.h>"]
    lines += [f"int case_{i}(void);" for i in range(1, len(sources) + 1)]
    lines += ["int main(void) {", "  volatile uint64_t *status=(void *)0x60000000;"]
    for i in range(1, len(sources) + 1):
        lines += [
            f"  *status=0x71000000u+{i};",
            f"  if (case_{i}()) return {i};",
            f"  *status=0x72000000u+{i};",
        ]
    lines += ["  return 0;", "}"]
    runner.write_text("\n".join(lines) + "\n")
    elf = out / "gemmini.elf"
    subprocess.run(
        common
        + [
            "-nostdlib",
            "-nostartfiles",
            "-Wl,--no-relax,--gc-sections",
            "-T",
            str(ROOT / "tests/cpu_smoke.ld"),
            str(ROOT / "tests/gemmini_start.S"),
            str(runner),
            str(ROOT / "tests/gemmini_runtime.c"),
            str(library / "buckyball.c"),
            *map(str, objects),
            "-lgcc",
            "-o",
            str(elf),
        ],
        check=True,
    )
    (out / "CASES.json").write_text(
        json.dumps({i: p.stem for i, p in enumerate(sources, 1)}, indent=2) + "\n"
    )
    simulation = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/check_cpu_smoke.py"),
            "--program-elf",
            str(elf),
            "--core-dir",
            str(args.core_dir.resolve()),
            "--output-dir",
            str(out / "simulation"),
            "--label",
            "whole Toy Gemmini regression",
            *(["--diagnostic-accelerator"] if args.diagnostic else []),
        ],
        check=False,
    )
    output = (out / "simulation/simulation.log").read_text()
    passed = [
        int(x, 16) & 0xFFFF
        for x in re.findall(r"CPU status = (0000000072[0-9a-f]+)", output)
    ]
    succeeded = simulation.returncode == 0 and passed == list(
        range(1, len(sources) + 1)
    )
    failures = [
        int(x, 16) & 0xFFFF
        for x in re.findall(r"CPU status = (00000000bad0[0-9a-f]+)", output)
    ]
    record = {
        "result": "PASS" if succeeded else "FAIL",
        "upstream_commit": manifest["commit"],
        "tests": [p.stem for p in sources],
        "test_count": len(sources),
        "passed_tests": [sources[i - 1].stem for i in passed],
        "failed_status_codes": failures,
        "runtime": (
            "bare-metal adapter; dimension adapted 16->8; "
            "unchanged upstream test bodies/ISA/matrix reference"
        ),
        "simulation_returncode": simulation.returncode,
    }
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"{len(passed)}/{len(sources)} upstream Gemmini workloads passed")
    if not succeeded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
