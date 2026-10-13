"""核验同步 RAM 与原寄存器路径逐周期等价，包括背压、绕回和中途复位。"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-elaboration", action="store_true")
    args = parser.parse_args()
    out = ROOT / "build/globalrob-check"
    out.mkdir(parents=True, exist_ok=True)
    commands = []
    if not args.skip_elaboration:
        commands.append((["sbt", "-batch", "runMain fpga.arty.linux.EmitGlobalRobCheck"],
                         "elaboration.log", 900))
    for command, name, timeout in commands:
        with (out / name).open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)
    # CIRCT appends named inline resources and the .f index to one emission.
    # Keep the untouched emission, compile only Verilog sections.
    parts = re.split(r'// ----- 8< ----- FILE "([^"]+)" ----- 8< -----',
                     (out / "GlobalRobCheck.sv").read_text())
    modules = [parts[0]]
    for name, body in zip(parts[1::2], parts[2::2]):
        if name.endswith((".sv", ".v")):
            modules.append(body)
        elif name == "firrtl_black_box_resource_files.f":
            if not all(line.strip().endswith(".v") for line in body.splitlines() if line.strip()):
                raise ValueError("Unexpected inline resource index")
        else:
            raise ValueError("Unexpected emitted resource: " + name)
    rtl = out / "GlobalRobCheck.sim.sv"
    rtl.write_text("\n".join(modules))
    commands = [(["verilator", "--binary", "--timing", "--assert", "-j", "4", "-Wno-fatal",
                   "-DBUCKYBALL_DISABLE_DPI", "--top-module", "tb", "--Mdir", str(out / "obj"),
                   str(rtl), str(ROOT / "tests/tb_globalrob.sv")],
                  "compile.log", 600),
                 ([str(out / "obj/Vtb")], "simulation.log", 60)]
    for command, name, timeout in commands:
        with (out / name).open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)
    transcript = (out / "simulation.log").read_text()
    if "PASS GLOBALROB RAM/register cycle comparison" not in transcript:
        raise ValueError("GlobalROB passing marker missing")
    record = {"result": "PASS", "cycle_equivalence": True,
              "coverage": ["accepted operand integrity", "ROB full", "pointer wrap",
                           "issue backpressure", "SubROB ownership stall", "mid-flight resets",
                           "concurrent allocation/issue/completion", "complete drain"],
              "rtl_sha256": hashlib.sha256((out / "GlobalRobCheck.sv").read_bytes()).hexdigest()}
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(transcript)


if __name__ == "__main__":
    main()
