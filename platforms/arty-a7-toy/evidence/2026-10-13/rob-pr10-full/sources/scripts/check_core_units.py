"""重新生成并验证 PE、FMA、移位、RF、查询与 SubROB 单元；不连接硬件。"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from offline_check import run_check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/core-unit-regressions"


def execute(name, command, marker=None, cwd=ROOT, timeout=900):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    (OUT / (name + ".log")).write_text(result.stdout + result.stderr)
    result.check_returncode()
    if marker and marker not in result.stdout:
        raise ValueError(f"Missing passing marker: {name}")
    return result.stdout


def unpack(path):
    pieces = re.split(r'// ----- 8< ----- FILE "([^"]+)" ----- 8< -----', path.read_text())
    modules = [pieces[0]]
    for name, body in zip(pieces[1::2], pieces[2::2]):
        if name.endswith((".sv", ".v")):
            modules.append(body)
        elif name != "firrtl_black_box_resource_files.f":
            raise ValueError("Unexpected emitted resource: " + name)
    output = OUT / (path.stem + ".sv")
    output.write_text("\n".join(modules))
    return output


def main():
    emitters = ["EmitPeChecks", "EmitFmaChecks", "EmitRoundShiftChecks", "EmitGroupQueryCheck", "EmitSubRobCheck"]
    execute("elaboration", ["sbt", "-batch"] + ["runMain fpga.arty.linux." + name for name in emitters])
    records = {}
    for label, raw, bench, marker in [
        ("round", "round-check/RoundShiftChecks.sv", "tb_round_shift.sv", "PASS ROUND_SHIFT"),
        ("group", "group-query-check/GroupQueryCheck.sv", "tb_group_query.sv", "PASS: 256 concurrent group queries"),
        ("subrob", "subrob-check/SubRobCheck.sv", "tb_subrob.sv", "PASS SUBROB")]:
        rtl = unpack(ROOT / "build" / raw)
        obj = OUT / (label + "-obj")
        execute(label + "-compile", ["verilator", "--binary", "--timing", "--assert", "-j", "4",
                 "-Wno-fatal", "-DBUCKYBALL_DISABLE_DPI", "--top-module", "tb", "--Mdir", str(obj),
                 str(rtl), str(ROOT / "tests" / bench)])
        execute(label, [str(obj / "Vtb")], marker, timeout=120)
        records[label] = "PASS"
    fma = unpack(ROOT / "build/fma-check/FmaPrecisionCheck.sv")
    obj = OUT / "fma-obj"
    execute("fma-compile", ["verilator", "--cc", "--exe", "--build", "-j", "4", "-Wno-fatal",
            "--top-module", "FmaPrecisionCheck", "--Mdir", str(obj), str(fma),
            str(ROOT / "tests/fma_differential.cpp")])
    execute("fma", [str(obj / "VFmaPrecisionCheck")], "PASS FMA_SHARED", ROOT / "build/fma-check", 120)
    records["fma"] = "PASS"
    rf = OUT / "fpu-rf.vvp"
    execute("rf-compile", ["iverilog", "-g2012", "-s", "tb", "-o", str(rf),
            str(ROOT / "rtl/FpuRfOriginal.sv"), str(ROOT / "rtl/FpuRfLvt.sv"), str(ROOT / "tests/tb_fpu_rf.sv")])
    execute("rf", ["vvp", str(rf)], "PASS FPU_RF_LVT", timeout=120)
    records["rf"] = "PASS"
    execute("pe", [sys.executable, str(ROOT / "tests/check_pe.py")], "PASS original/LUT/DSP PE")
    records["pe"] = "PASS"
    record = {"result": "PASS_UNIT_REGRESSIONS", "physical_hardware_tested": False, "tests": records,
              "generated_rtl": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in OUT.glob("*.sv")}}
    (OUT / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print("PASS core units: PE/formal quantizer, FMA, round shift, FPU RF, group query and SubROB")


if __name__ == "__main__":
    run_check(main, OUT)
