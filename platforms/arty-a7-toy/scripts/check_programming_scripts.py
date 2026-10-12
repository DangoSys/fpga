"""离线注入 Vivado API 返回值、异常与配置状态，检查实际 Tcl 入口。"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from offline_check import run_check

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tclsh", default=shutil.which("tclsh"))
    args = parser.parse_args()
    if not args.tclsh:
        raise RuntimeError("Install Tcl or supply --tclsh")
    out = ROOT / "build/programming-check"
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    for script in ["program_arty.tcl", "backup_flash.tcl", "program_flash.tcl"]:
        faults = ["none", "device_error", "done_low", "eos_low", "crc_error"]
        if script != "program_arty.tcl":
            faults += ["readback_error", "short_backup"]
        if script == "program_flash.tcl":
            faults += ["cfgmem_error"]
        for fault in faults:
            with tempfile.TemporaryDirectory(dir=out) as directory:
                work = Path(directory)
                bit = work / "input.bit"
                bit.write_bytes(b"offline fixture")
                command = [args.tclsh, str(ROOT / "tests/mock_programming.tcl"),
                           str(ROOT / "board" / script), fault, str(bit), str(work / "backup.bin")]
                result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                transcript = result.stdout + result.stderr
                (out / f"{script}-{fault}.log").write_text(transcript, encoding="utf-8")
                if fault == "none":
                    if result.returncode or "MOCK_SUCCESS" not in transcript:
                        raise ValueError(f"Documented success return rejected: {script}: {transcript}")
                else:
                    if result.returncode == 0 or "MOCK_FAILURE" not in transcript:
                        raise ValueError(f"Injected failure accepted: {script}/{fault}")
                    if "PASS FLASH_PROGRAM_VERIFY" in transcript or "ARTY_JTAG_PROGRAMMED:" in transcript:
                        raise ValueError("False success marker")
                    if fault != "cfgmem_error" and "program_flash" in transcript.split("MOCK_EVENTS", 1)[1].splitlines()[0]:
                        raise ValueError("Flash programming reached after an earlier failure")
                cases.append({"script": script, "fault": fault, "result": "PASS"})
    record = {"result": "PASS_OFFLINE_TCL_CONTRACTS", "physical_hardware_tested": False,
              "cases": cases}
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"PASS programming scripts: {len(cases)} documented-return/status/error cases; no hardware")


if __name__ == "__main__":
    run_check(main, ROOT / "build/programming-check")
