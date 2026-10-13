"""为 ROB 操作数候选显式绑定 BRAM，核对 profile 与已有存储器几何参数。"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from prepare_fpga_memories import unpack_emission, validate

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-memory-manifest", type=Path, required=True)
    args = parser.parse_args()
    raw = ROOT / "build/serial-raw/ToyLinuxChip.sv"
    profile = json.loads((ROOT / "build/serial-raw/ToyLinuxChip.profile.json").read_text())
    expected = json.loads((evidence_path("2026-10-11/ToyLinuxChip.profile.json")).read_text())
    if profile != expected:
        raise ValueError("Optimization changed the architectural hardware profile")
    _, memories, config = unpack_emission(raw.read_text())
    validate(memories, config)
    operands = [m for m in memories if any("robOperands" in h for h in m["hierarchy"])]
    if len(operands) != 1:
        raise ValueError("Expected one ROB operand memory type")
    operand = operands[0]
    if (operand["depth"], operand["width"], operand["read"], operand["write"],
            operand["readwrite"], operand["masked"], len(operand["hierarchy"])) != (16, 128, 1, 1, 0, False, 1):
        raise ValueError("Unexpected ROB memory geometry or topology")
    baseline = json.loads(args.baseline_memory_manifest.read_text())
    if baseline["core_rtl_sha256"] != "4c6aacf64660bbbf14b1114e8d5e4439d6a4e1427aaf1f681c6a4f618f2d2779":
        raise ValueError("Wrong baseline memory manifest")
    def signature(memory):
        return tuple(memory.get(k) for k in
                     ("depth", "width", "read", "write", "readwrite", "masked", "mask_granularity"))
    before = sorted((signature(m), len(m["hierarchy"])) for m in baseline["memories"])
    after = sorted((signature(m), len(m["hierarchy"])) for m in memories if m != operand)
    if before != after:
        raise ValueError("An existing memory geometry/topology changed")
    subprocess.run([sys.executable, str(ROOT / "scripts/prepare_fpga_memories.py"), str(raw),
                    "--output-dir", str(ROOT / "build/serial-bound"),
                    "--block-memory", operand["module_name"]], check=True, timeout=60)
    subprocess.run([sys.executable, str(ROOT / "scripts/bind_fpu_rf.py")], check=True, timeout=60)
    record = {"result": "PREPARED_NOT_VALIDATED", "architectural_profile_unchanged": True,
              "existing_memory_geometry_unchanged": True, "rob_operand_memory": operand,
              "rob_operand_ram_style": "block", "core_rtl_sha256": digest(ROOT / "build/serial-bound/ToyLinuxChip.sv"),
              "memory_rtl_sha256": digest(ROOT / "build/serial-bound/FpgaMemories.sv")}
    (ROOT / "build/ROB_RAM_PREPARED.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
