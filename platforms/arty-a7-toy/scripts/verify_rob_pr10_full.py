"""离线核验本轮完整实现/RTL 档案，可另传位流检查实际摘要；不访问硬件。"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "evidence/2026-10-13/rob-pr10-full"


def read(name):
    return json.loads((ARCHIVE / name).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", type=Path)
    args = parser.parse_args()
    manifest = read("MANIFEST.json")
    for name, metadata in manifest["files"].items():
        path = ARCHIVE / name
        require(sha(path) == metadata["sha256"] and path.stat().st_size == metadata["bytes"], name)
    result = read("RESULT.json")
    require(result["result"] == "PASS_ROB_PR10_FULL_VALIDATION", "full result")
    require(result["engineering_prerelease"] and not result["physical_hardware_tested"], "physical qualification")
    require(not result["physical_mig_simulated"] and not result["flash_boot_tested"], "simulation scope")
    run = read("implementation/RUN.json")
    require(run["status"] == "COMPLETED" and run["exit_code"] == 0 and run["bitstream_generated"], "implementation")
    require(run["candidate_core_unchanged"] and run["candidate_memory_unchanged"], "generated inputs")
    require(run["timeout_seconds"] == 3600 and run["elapsed_seconds"] < 3600, "timeout")
    require(run["part"] == result["part"] == "xc7a100tcsg324-1", "target")
    for name, expected in run["board_sources"].items():
        require(sha(ARCHIVE / "sources" / name) == expected, name)
    inputs = read("INPUTS.json")
    for name, expected in inputs["files"].items():
        require(sha(ARCHIVE / "sources" / name) == expected, name)
    timing = (ARCHIVE / "implementation/routed-timing.rpt").read_text()
    require("All user specified timing constraints are met." in timing, "timing summary")
    rows = timing.split("WNS(ns)", 1)[1].splitlines()
    values = next(line.split() for line in rows if re.match(r"\s+-?\d+\.\d+", line))
    require(float(values[0]) == result["timing"]["wns_ns"] >= 0 and
            float(values[4]) == result["timing"]["whs_ns"] >= 0, "slack")
    require(all(float(values[i]) == 0 for i in [1, 2, 5, 6]), "violating endpoints")
    for name in ["drc.rpt", "cdc.rpt"]:
        require(not re.search(r"\b(?:Critical|Error)\b", (ARCHIVE / "implementation" / name).read_text()), name)
    route = (ARCHIVE / "implementation/route-status.rpt").read_text()
    require(bool(re.search(r"nets with routing errors\.+\s*:\s*0\s*:", route)), "route errors")
    linux = read("tests/board-linux-final/RESULT.json")
    require(linux["result"] == "PASS_RTL_LINUX_USERSPACE" and not linux["physical_board_tested"], "Linux scope")
    log = (ARCHIVE / "tests/board-linux-final/simulation.log").read_text()
    require(all(marker in log for marker in linux["checks"]), "Linux markers")
    require(linux["payload_sha256"] == result["payload_sha256"], "Linux input")
    regressions = read("BOARD_REGRESSION.json")["tests"]
    require(len(regressions) == 4 and all(case["result"] == "PASS" for case in regressions.values()), "board cases")
    baseline = json.loads((evidence_path("2026-10-12/rob-ram/tests/BOARD_REGRESSION.json")).read_text())
    require(all(case["cycles"] == baseline["tests"][name]["cycles"] for name, case in regressions.items()), "same cycles")
    require(read("tests/core-unit-regressions/RESULT.json")["result"] == "PASS_UNIT_REGRESSIONS", "units")
    require(read("tests/fpu-shared/RESULT.json")["vector_count"] == 1536, "floating vectors")
    require(read("tests/board-cdc/RESULT.json")["result"] == "PASS_BOARD_CDC", "actual CDC IP")
    uart = read("tests/board-uart-boot/RESULT.json")
    require(uart["result"] == "PASS_UART_LOAD_VERIFY_BOOT" and uart["bytes_verified"] == 110592, "UART boot")
    require(not uart["testbench_cpu_release_override"] and not uart["preloaded_ddr_image"], "UART loader boundary")
    mmio = read("tests/board-mmio-error/RESULT.json")
    require(mmio["result"] == "PASS_CPU_MMIO_SLVERR" and mmio["synchronous_traps_observed"] == 0, "MMIO scope")
    require("CPU did not receive SLVERR" in (ARCHIVE / "tests/mmio-old-counterexample/simulation.log").read_text(), "old negative")
    if args.bitstream:
        require(sha(args.bitstream) == result["bitstream_sha256"], "actual bitstream")
    print(f"PASS ROB/PR10 full archive: {len(manifest['files'])} artifacts; implementation, units, CPU/Gemmini/Linux and actual CDC")


if __name__ == "__main__":
    main()
