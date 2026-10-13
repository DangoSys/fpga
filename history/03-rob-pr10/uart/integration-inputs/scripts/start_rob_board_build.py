"""以独立候选记录执行同一整板流程；不继承旧位流的资格结论。"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from start_board_build import ROOT, TZ, save, sha, worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        out = args.worker.resolve()
        worker(out)
        record = json.loads((out / "RUN.json").read_text())
        record["candidate_core_unchanged"] = sha(ROOT / "build/serial-bound/ToyLinuxChip.sv") == record["core_sha256"]
        record["candidate_memory_unchanged"] = sha(ROOT / "build/serial-bound/FpgaMemories.sv") == record["memory_sha256"]
        if not record["candidate_core_unchanged"] or not record["candidate_memory_unchanged"]:
            record["status"] = "INPUT_CHANGED_REJECTED"
        save(out / "RUN.json", record)
        return
    prepared = json.loads((ROOT / "build/ROB_RAM_PREPARED.json").read_text())
    for path in ["build/globalrob-check/RESULT.json", "build/BOARD_REGRESSION.json"]:
        if json.loads((ROOT / path).read_text())["result"] != "PASS":
            raise ValueError("Candidate regression has not passed: " + path)
    core = ROOT / "build/serial-bound/ToyLinuxChip.sv"
    memories = ROOT / "build/serial-bound/FpgaMemories.sv"
    if sha(core) != prepared["core_rtl_sha256"] or sha(memories) != prepared["memory_rtl_sha256"]:
        raise ValueError("Candidate inputs changed after preparation")
    for path in (ROOT / "build").glob("board-*/RUN.json"):
        if json.loads(path.read_text())["status"] in ("CREATED", "RUNNING"):
            raise ValueError("An isolated board build is already active")
    out = ROOT / "build" / ("board-rob-ram-" + datetime.now(TZ).strftime("%Y%m%d-%H%M%S"))
    out.mkdir()
    shutil.copytree(ROOT / "board", out / "inputs/board")
    files = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / "board").rglob("*") if p.is_file()}
    script = out / "inputs/board/build_board.tcl"
    # Keep the input snapshot for audit, execute the identical script at its
    # normal root so relative HDL/IP paths resolve without rewriting Tcl.
    record = {"status": "CREATED", "optimization": "ROB_OPERAND_BRAM", "timeout_seconds": 3600,
              "termination_grace_seconds": 15, "part": "xc7a100tcsg324-1",
              "core_sha256": sha(core), "memory_sha256": sha(memories), "board_sources": files,
              "execution_script": str(ROOT / "board/build_board.tcl"), "execution_script_sha256": sha(script),
              "core_clock_hz": 25000000, "uart_baud": 1000000,
              "architectural_profile_unchanged": True, "flash_boot": False,
              "physical_boot_tested": False, "inherits_baseline_hardware_qualification": False}
    save(out / "RUN.json", record)
    with (out / "launcher.log").open("w") as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(out)],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True)
    print(json.dumps({"output_directory": str(out), "worker_pid": process.pid, "timeout_seconds": 3600}))


if __name__ == "__main__":
    main()
