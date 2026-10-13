"""注入检查失败，验证三种实际入口不会遗留上次 PASS；不连接硬件。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from offline_check import run_check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/runner-status-check"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", help="仅用旧源码反测，预期复现遗留 PASS")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    runners = [("check_board.py", "board-unit", "PASS"),
               ("check_programming_scripts.py", "programming-check", "PASS_OFFLINE_TCL_CONTRACTS"),
               ("check_flash_guards.py", "flash-guard-check", "PASS_FLASH_GUARDS_NORMAL_AND_OPTIMIZED")]
    for script, directory, old_pass in runners:
        source = ROOT / "scripts" / script
        data = source.read_bytes() if not args.baseline_ref else subprocess.check_output(
            ["git", "show", f"{args.baseline_ref}:platforms/arty-a7-toy/scripts/{script}"], cwd=ROOT)
        with tempfile.TemporaryDirectory(dir=OUT) as temporary:
            work = Path(temporary)
            (work / "scripts").mkdir()
            (work / "tests").mkdir()
            (work / "scripts" / script).write_bytes(data)
            helper = ROOT / "scripts/offline_check.py"
            if helper.exists():
                shutil.copy2(helper, work / "scripts/offline_check.py")
            result_file = work / "build" / directory / "RESULT.json"
            result_file.parent.mkdir(parents=True)
            result_file.write_text(json.dumps({"result": old_pass}))
            if script == "check_board.py":
                (work / "tests/PLATFORM_PORTS_MANIFEST.json").write_text(json.dumps({"stub_sha256": "0" * 64}))
                (work / "tests/ToyLinuxChipPorts.sv").write_text("// injected fixture mismatch\n")
                extra = []
            elif script == "check_programming_scripts.py":
                # A child fails before any hardware operation; Python is the injected interpreter.
                (work / "tests/mock_programming.tcl").write_text("raise RuntimeError('INJECTED_CHECK_FAILURE')\n")
                extra = ["--tclsh", sys.executable]
            else:
                (work / "tests/flash_guard_probe.py").write_text("raise RuntimeError('INJECTED_CHECK_FAILURE')\n")
                extra = []
            process = subprocess.run([sys.executable, str(work / "scripts" / script)] + extra,
                                     capture_output=True, text=True, timeout=30)
            status = json.loads(result_file.read_text())
            log = process.stdout + process.stderr + "\nOBSERVED_RESULT " + json.dumps(status) + "\n"
            (OUT / (script + ".log")).write_text(log, encoding="utf-8")
            if process.returncode == 0:
                raise ValueError("Failure injection did not reach the actual runner")
            expected = old_pass if args.baseline_ref else "FAILED"
            if status["result"] != expected:
                raise ValueError(f"{script}: expected {expected}, got {status}")
            cases.append({"script": script, "source_sha256": hashlib.sha256(data).hexdigest(),
                          "exit_code": process.returncode, "observed_result": status["result"], "result": "PASS"})
    record = {"result": "PASS_EXPECTED_STALE_BASELINE" if args.baseline_ref else "PASS_RUNNER_FAILURE_STATUS",
              "baseline_ref": args.baseline_ref, "physical_hardware_tested": False, "cases": cases}
    (OUT / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"PASS runner failure status: {len(cases)} actual entrypoints; baseline={args.baseline_ref or 'current'}")


if __name__ == "__main__":
    run_check(main, OUT)
