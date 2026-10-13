"""Execute original-FMA oracle vectors as real H/S/D Rocket instructions."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline-core", type=Path,
                    default=ROOT.parent / "toy-a7-all-dsp-20261010/build/serial-bound",
                    help="含 ToyLinuxChip.sv 和 FpgaMemories.sv 的原独立 FMA 核心目录")
args = parser.parse_args()
out = ROOT / "build/fpu-shared"
out.mkdir(parents=True, exist_ok=True)
vectors = ROOT / "build/fma-check/vectors.csv"
rows = []
for line in vectors.read_text().splitlines():
    values = line.split(",")
    rows.append([*map(int, values[:4]), *[int(x, 16) for x in values[4:]]])
assert len(rows) == 1536
code = ["#include <stdint.h>",
        "struct Vector { uint64_t a,b,c,expected; unsigned tag,kind,op,rm,flags; };",
        "static const struct Vector vectors[] = {"]
for tag, kind, op, rm, a, b, c, expected, flags in rows:
    code.append(f"  {{0x{a:x}ULL,0x{b:x}ULL,0x{c:x}ULL,0x{expected:x}ULL,{tag},{kind},{op},{rm},{flags}}},")
code += ["};", "static uint64_t execute(const struct Vector *v, uint64_t *flags) {",
         "  uint64_t result = 0, f;", '  asm volatile("csrw frm, %0" :: "r"((uint64_t)v->rm));']
for tag, precision, load, store in ((0, "h", "flh", "fsh"), (1, "s", "flw", "fsw"), (2, "d", "fld", "fsd")):
    code += [f"  {'if' if tag == 0 else 'else if'} (v->tag == {tag}) {{"]
    for kind, op, instruction, operands in (
        (0, 0, "fmadd", "ft3, ft0, ft1, ft2, dyn"),
        (0, 1, "fmsub", "ft3, ft0, ft1, ft2, dyn"),
        (0, 2, "fnmsub", "ft3, ft0, ft1, ft2, dyn"),
        (0, 3, "fnmadd", "ft3, ft0, ft1, ft2, dyn"),
        (1, 0, "fadd", "ft3, ft0, ft2, dyn"),
        (1, 1, "fsub", "ft3, ft0, ft2, dyn"),
        (2, 0, "fmul", "ft3, ft0, ft1, dyn"),
    ):
        code += [f"    if (v->kind == {kind} && v->op == {op}) {{",
                 '      asm volatile("csrw fflags, zero\\n"',
                 f'                   "{load} ft0, 0(%2)\\n{load} ft1, 8(%2)\\n{load} ft2, 16(%2)\\n"',
                 f'                   "{instruction}.{precision} {operands}\\n{store} ft3, 0(%1)\\nfrflags %0\\n"',
                 '                   : "=r"(f) : "r"(&result), "r"(v)',
                 '                   : "memory", "ft0", "ft1", "ft2", "ft3");',
                 "    }"]
    code += ["  }"]
code += ["  *flags = f; return result;", "}", "static int dependency_benchmark(void) {",
         "  volatile uint64_t *status = (volatile uint64_t *)0x60000000ULL;"]
for tag, precision, load, store, one, expected in (
    (0, "h", "flh", "fsh", 0x3c00, 0x6401),
    (1, "s", "flw", "fsw", 0x3f800000, 0x44802000),
    (2, "d", "fld", "fsd", 0x3ff0000000000000, 0x4090040000000000),
):
    code += ["  {", f"    uint64_t one=0x{one:x}ULL, result=0, begin, end;",
             f'    asm volatile("{load} ft0, 0(%2)\\n{load} ft1, 0(%2)\\nli t0, 32\\ncsrr %0, cycle\\n"',
             f'                 "1: .rept 32\\nfadd.{precision} ft0, ft0, ft1, rne\\n.endr\\n"',
             f'                 "addi t0, t0, -1\\nbnez t0, 1b\\n{store} ft0, 0(%3)\\ncsrr %1, cycle\\n"',
             '                 : "=&r"(begin), "=&r"(end) : "r"(&one), "r"(&result)',
             '                 : "memory", "t0", "ft0", "ft1");',
             f"    if (result != 0x{expected:x}ULL) return 32;",
             f"    status[0] = 0x{0x7300000000000000 | (tag << 32):016x}ULL | (end-begin);", "  }"]
code += ["  return 0;", "}", "int main(void) {",
         "  volatile uint64_t *status = (volatile uint64_t *)0x60000000ULL;",
         "  for (unsigned i = 0; i < sizeof(vectors)/sizeof(vectors[0]); ++i) {",
         "    uint64_t flags; uint64_t actual = execute(&vectors[i], &flags);",
         "    if (actual != vectors[i].expected || flags != vectors[i].flags) {",
         "      status[2] = i; status[3] = actual; status[4] = vectors[i].expected;",
         "      status[5] = flags; status[6] = vectors[i].flags; return 31;", "    }", "  }",
         "  return dependency_benchmark();", "}"]
source = out / "fpu_vectors.c"
source.write_text("\n".join(code) + "\n")
elf = out / "fpu_vectors.elf"
subprocess.run([
    "riscv64-unknown-elf-gcc", "-O2", "-ffreestanding", "-fno-builtin", "-ffunction-sections",
    "-fdata-sections", "-msmall-data-limit=0", "-mcmodel=medany", "-march=rv64imafdc_zicsr_zifencei_zfh",
    "-mabi=lp64d", "-nostdlib", "-nostartfiles", "-Wl,--no-relax,--gc-sections", "-T",
    str(ROOT / "tests/cpu_smoke.ld"), str(ROOT / "tests/gemmini_start.S"), str(source),
    str(ROOT / "tests/gemmini_runtime.c"), "-lgcc", "-o", str(elf)], check=True)
subprocess.run([sys.executable, str(ROOT / "tests/check_cpu_smoke.py"), "--program-elf", str(elf),
                "--output-dir", str(out / "simulation"), "--label", "whole Toy shared FPU 1536 oracle vectors"], check=True)
baseline_output = out / "baseline-simulation"
subprocess.run([sys.executable, str(ROOT / "tests/check_cpu_smoke.py"), "--program-elf", str(elf),
                "--core-dir", str(args.baseline_core),
                "--output-dir", str(baseline_output), "--label", "whole Toy baseline FPU 1536 oracle vectors"], check=True)
def measures(path):
    log = (path / "simulation.log").read_text()
    cycles = {int(tag): int(value, 16) for tag, value in re.findall(r"CPU status = 7300000([012])([0-9a-f]{8})", log)}
    assert set(cycles) == {0, 1, 2}
    return cycles
new_cycles = measures(out / "simulation")
old_cycles = measures(baseline_output)
record = {"result": "PASS", "vector_count": len(rows), "precision_counts": [sum(row[0] == tag for row in rows) for tag in range(3)],
          "rounding_modes": sorted({row[3] for row in rows}), "vector_sha256": hashlib.sha256(vectors.read_bytes()).hexdigest(),
          "oracle": "unchanged original H/S/D FPUFMAPipe data and exception flags",
          "regression": json.loads((out / "simulation/RESULT.json").read_text()),
          "baseline_regression": json.loads((baseline_output / "RESULT.json").read_text()),
          "dependency_benchmark": {"operation": "1024 dependent FADD; groups of 32, including loop overhead and final store",
                                   "baseline_cycles_HSD": old_cycles, "candidate_cycles_HSD": new_cycles,
                                   "delta_cycles_HSD": {tag: new_cycles[tag] - old_cycles[tag] for tag in range(3)}}}
assert record["regression"]["test_binary_sha256"] == record["baseline_regression"]["test_binary_sha256"]
(out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
