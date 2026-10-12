"""核验 ROB RAM 候选的两次实物回归、原始日志和输入摘要。"""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "evidence/2026-10-12/rob-ram-hardware"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = read(ARCHIVE / "MANIFEST.json")
    for name, metadata in manifest["files"].items():
        path = (ARCHIVE / name).resolve()
        assert path.is_relative_to(ARCHIVE.resolve()), name
        assert path.stat().st_size == metadata["bytes"] and sha(path) == metadata["sha256"], name
    summary = read(ARCHIVE / "HARDWARE_RESULT.json")
    assert summary["result"] == "PASS_ROB_RAM_PHYSICAL_LINUX_AND_GEMMINI"
    assert summary["flash_written"] is False and summary["model_end_to_end_tested"] is False
    implementation = read(ARCHIVE / "implementation/RUN.json")
    assert implementation["status"] == "COMPLETED" and implementation["exit_code"] == 0
    assert implementation["candidate_core_unchanged"] and implementation["candidate_memory_unchanged"]
    assert implementation["core_sha256"] == summary["core_rtl_sha256"]
    assert implementation["memory_sha256"] == summary["memory_rtl_sha256"]
    assert implementation["part"] == summary["part"] == "xc7a100tcsg324-1"
    first = read(ARCHIVE / "first-pass/RESULT.json")
    build = read(ARCHIVE / "software/LINUX_GEMMINI_BUILD.json")
    assert not first.get("configuration_reused", False)
    assert first["ddr_readback_bytes"] == build["payload_bytes"] == summary["ddr_readback_bytes"]
    transfer = (ARCHIVE / "first-pass/transfer-console.log").read_text(encoding="utf-8")
    expected = f"PASS FULL_DDR_READBACK bytes={build['payload_bytes']} seconds={first['ddr_transfer_seconds']}"
    assert expected in transfer and "PASS LINUX_BOOT" in transfer
    program = (ARCHIVE / "first-pass/program.log").read_text(encoding="utf-8")
    assert "ARTY_JTAG_PROGRAMMED:" in program and "xc7a100t" in program
    session = read(ARCHIVE / "SESSION.json")
    assert session["exit_code"] == 0 and session["timeout_seconds"] == 3600
    for directory in ["first-pass", "repeat-pass"]:
        result = read(ARCHIVE / directory / "RESULT.json")
        assert result["bitstream_sha256"] == summary["bitstream_sha256"]
        assert result["payload_sha256"] == build["payload_sha256"] == summary["payload_sha256"]
        subprocess.run([
            sys.executable, str(ROOT / "scripts/verify_linux_gemmini.py"),
            "--build-record", str(ARCHIVE / "software/LINUX_GEMMINI_BUILD.json"),
            "--hardware-result", str(ARCHIVE / directory / "RESULT.json"),
            "--expected-bit-sha256", summary["bitstream_sha256"],
        ], check=True, timeout=30, stdout=subprocess.DEVNULL)
    assert read(ARCHIVE / "repeat-pass/LOAD_RESULT.json") == first
    watchdog = read(ARCHIVE / "watchdog/RESULT.json")
    assert watchdog["result"] == "PASS_WATCHDOG_SUCCESS_FAILURE_TIMEOUT_AND_REAP"
    assert [case["exit_code"] for case in watchdog["cases"]] == [0, 1, 137]
    raw = (ARCHIVE / "watchdog/check.log").read_bytes()
    for index, case in enumerate(watchdog["cases"]):
        assert case["watcher_alive_rc"] == 1
        assert re.search(rb"(?:^|\n)WATCH_SELF_" + str(index).encode() + rb":"
                         + str(case["exit_code"]).encode() + rb"\r*\n", raw)
        assert re.search(rb"(?:^|\n)WATCH_REAP_" + str(index).encode() + rb":1\r*\n", raw)
    live = read(ARCHIVE / "post-check/RESULT.json")
    assert live["result"] == "PASS_POST_TEST_LIVE_SHELL" and live["watchdog_alive_rc"] == 1
    assert live["MemTotal_kib"] > 200000 and live["MemAvailable_kib"] > 0
    assert not live["flash_written"] and not live["configuration_changed"]
    assert live["uart_latency_restored_ms"] == 16
    for name, expected in summary["execution_sources"].items():
        assert sha(ARCHIVE / "sources" / name) == expected, name
    print(f"PASS ROB RAM physical archive: {len(manifest['files'])} files; full DDR readback; two 15-workload runs")


if __name__ == "__main__":
    main()
