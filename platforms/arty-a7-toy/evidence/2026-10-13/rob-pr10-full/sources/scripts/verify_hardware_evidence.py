"""Check the immutable physical bring-up archive without contacting hardware."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "evidence/2026-10-12/hardware"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = read(ARCHIVE / "MANIFEST.json")
    assert manifest["run_date"] == "2026-10-12"
    assert manifest["time_zone"] == "Asia/Shanghai"
    for name, metadata in manifest["files"].items():
        assert sha(ARCHIVE / name) == metadata["sha256"], name
    # Historical programming evidence binds the archived script, not later
    # revised entry points. Current sources have their own SOURCE_LOCK/tests.
    assert sha(ARCHIVE / "program_arty.tcl") == manifest["files"]["program_arty.tcl"]["sha256"]
    assert sha(ROOT / "host/load.py") == manifest["host_loader_sha256"]
    hardware = read(ARCHIVE / "HARDWARE_RESULT.json")
    implementation = read(ROOT / "evidence/2026-10-11/BOARD_RESULT.json")
    assert hardware["result"] == "PASS_HARDWARE_LOAD_AND_LINUX_CHECK"
    assert hardware["physical_linux_boot_tested"]
    assert hardware["bitstream_sha256"] == implementation["bitstream_sha256"]
    assert hardware["payload_sha256"] == implementation["linux"]["payload_sha256"]
    for name, expected in hardware["evidence_sha256"].items():
        assert sha(ARCHIVE / name) == expected, name
    assert hardware["physical_board_revision"] == "unknown"
    assert not hardware["hardware_gemmini_operator_tests_run"]
    assert not hardware["hardware_fp16_fp32_exhaustive_tests_run"]
    assert hardware["configuration"] == "volatile FPGA SRAM"
    assert hardware["verified_ddr_bytes"] == hardware["payload_bytes"] == 17409032
    assert hardware["complete_payload_ddr_readback"] == "PASS"
    assert hardware["system_check_process_exit_status"] == 0
    assert hardware["live_shell"] == "PASS"
    assert hardware["uart_latency_restored_ms"] == 16
    program = (ARCHIVE / "program.log").read_bytes()
    assert b"End of startup status: HIGH" in program
    assert b"ARTY_JTAG_PROGRAMMED:" in program
    assert b"Device xc7a100t" in program
    load = (ARCHIVE / "load-and-linux.log").read_bytes()
    progress = [(int(done), int(total)) for done, total in
                re.findall(rb"Verified (\d+)/(\d+) bytes", load)]
    assert progress[0][0] == 256
    assert all(total == hardware["payload_bytes"] for _, total in progress)
    assert all(b[0] - a[0] == 65536 for a, b in zip(progress, progress[1:]))
    assert progress[-1][0] >= hardware["payload_bytes"] - 65536
    assert b"Full readback passed; CPU started after 544.1s." in load
    console = (ARCHIVE / "linux-console.log").read_bytes()
    checks = {"VM_COPY_ON_WRITE", "VM_PAGE_PROTECTION", "FP64_PROCESS_CONTEXT",
              "LINUX_TIMER", "LINUX_SYSTEM_CHECK"}
    assert set(hardware["linux_checks"]) == checks
    for check in checks:
        assert hardware["linux_checks"][check] == "PASS"
        assert ("PASS " + check).encode() in console, check
    assert b"OpenSBI v1.9" in console and b"Linux version 6.6.0" in console
    assert b"elapsed_ns=103836000" in console
    first = (ARCHIVE / "live-console-first.log").read_bytes()
    assert re.search(rb"(?:^|\n)HARDWARE_RC:0\r*\n", first)
    live = (ARCHIVE / "live-console.log").read_bytes()
    assert b"KERNEL:Linux version 6.6.0" in live
    assert b"MEMORY:MemTotal: 245784 kB" in live
    assert re.search(rb"(?:^|\n)FPGA_LIVE_DONE\r*\n", live)
    print(f"PASS physical hardware archive: {len(manifest['files'])} original artifacts; "
          "complete DDR image readback, five Linux checks and live shell")


if __name__ == "__main__":
    verify()
