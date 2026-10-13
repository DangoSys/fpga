"""只在 build 中注入 RTL 错误，核验 AXI 用例的检错能力；不改生产源码。"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
from offline_check import run_check

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/backpressure-mutation"
OLD = evidence_path("2026-10-12/pr10-review")


def main():
    original = (ROOT / "board/axi_scu.sv").read_text()
    condition = "if(bvalid && bready) bvalid<=0;"
    if original.count(condition) != 1:
        raise ValueError("SCU mutation target changed; review this oracle")
    mutant = OUT / "scu-mutant.sv"
    mutant.write_text(original.replace(condition, "if(bvalid) bvalid<=0;"))
    common = [ROOT / "board" / name for name in
              ["axi_fullwidth.sv", "ddr_uart_loader.sv", "loader_axi.sv",
               "uart_rx.sv", "uart_tx.sv", "flash_spi_byte.sv"]]
    common += [ROOT / "tests/ToyLinuxChipPorts.sv"]
    cases = []
    inputs = [("old-test", ROOT / "board/toy_a7_platform.sv", mutant,
               OLD / "sources/tests/tb_platform_bresp.sv", 0),
              ("new-test", ROOT / "board/toy_a7_platform.sv", mutant,
               ROOT / "tests/tb_platform_bresp.sv", 1),
              ("old-response", OLD / "old-platform.sv", ROOT / "board/axi_scu.sv",
               ROOT / "tests/tb_platform_bresp.sv", 1)]
    for label, platform, scu, bench, expected in inputs:
        executable = OUT / label
        sources = [platform, scu, bench] + common
        compiled = subprocess.run(["iverilog", "-g2012", "-s", "tb_platform_bresp", "-o",
                                   str(executable)] + [str(path) for path in sources],
                                  capture_output=True, text=True, timeout=60)
        (OUT / (label + "-compile.log")).write_text(compiled.stdout + compiled.stderr)
        compiled.check_returncode()
        result = subprocess.run(["vvp", str(executable)], capture_output=True, text=True, timeout=60)
        log = result.stdout + result.stderr
        (OUT / (label + ".log")).write_text(log)
        marker = {"old-test": "PASS platform AXI B response", "new-test": "valid=0",
                  "old-response": "actual=01 expected=10"}[label]
        if result.returncode != expected or marker not in log:
            raise ValueError(f"Mutation oracle failed: {label}: {log}")
        cases.append({"case": label, "exit_code": result.returncode, "expected_exit_code": expected,
                      "result": "PASS", "sources": {Path(os.path.relpath(path, ROOT)).as_posix():
                      hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}})
    record = {"result": "PASS_MUTATION_ORACLES", "physical_hardware_tested": False, "cases": cases}
    (OUT / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print("PASS mutation oracles: old test misses premature BVALID drop; new test rejects it and old response bug")


if __name__ == "__main__":
    run_check(main, OUT)
