"""Check the preserved Flash implementation and physical cold-start evidence."""

import hashlib
import json
from pathlib import Path
import re

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = evidence_path("2026-10-12/flash")
CHECKS = {
    "VM_COPY_ON_WRITE",
    "VM_PAGE_PROTECTION",
    "FP64_PROCESS_CONTEXT",
    "LINUX_TIMER",
    "LINUX_SYSTEM_CHECK",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = read(ARCHIVE / "MANIFEST.json")
    for name, expected in manifest["files"].items():
        assert sha(ARCHIVE / name) == expected, name
    record = read(ARCHIVE / "FLASH_RESULT.json")
    run = read(ARCHIVE / "implementation/RUN.json")
    software = read(ARCHIVE / "software/MANIFEST.json")
    packed = read(ARCHIVE / "software/FLASH_IMAGE.json")
    assert run["status"] == "COMPLETED" and run["exit_code"] == 0
    assert run["flash_boot"] and run["bitstream_generated"]
    assert run["timeout_seconds"] == 3600 and run["elapsed_seconds"] < 3600
    for name, expected in run["board_sources"].items():
        assert sha(ARCHIVE / "sources" / name) == expected, name
    assert record["part"] == run["part"] == "xc7a100tcsg324-1"
    assert run["core_sha256"] == software["original_core_sha256"]
    assert software["only_module_replaced"] == "TLROM"
    assert software["dtb_address"] == "0x11000" and software["rom_bytes"] == 8192
    assert record["payload_sha256"] == software["payload_sha256"]
    assert record["bitstream_sha256"] == packed["bitstream_sha256"]
    previous = read(evidence_path("2026-10-11/BOARD_RESULT.json"))
    assert record["payload_sha256"] == previous["linux"]["payload_sha256"]

    labels = {
        "Slice LUTs": "LUT",
        "Slice Registers": "FF",
        "Block RAM Tile": "BRAM_tiles",
        "DSPs": "DSP",
        "Slice": "Slice",
    }
    area = {}
    for line in (
        (ARCHIVE / "implementation/routed-utilization.rpt").read_text().splitlines()
    ):
        fields = [field.strip() for field in line.split("|")]
        if len(fields) > 3 and fields[1] in labels:
            area[labels[fields[1]]] = float(fields[2])
    assert area == record["routed_resources"]
    timing = (ARCHIVE / "implementation/routed-timing.rpt").read_text()
    match = re.search(
        r"WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([\d.-]+)\s+([\d.-]+)\s+(\d+)\s+(\d+)\s+([\d.-]+)\s+([\d.-]+)",
        timing,
    )
    assert match and float(match[1]) == record["wns_ns"] >= 0
    assert float(match[2]) == float(match[6]) == 0
    assert float(match[5]) == record["whs_ns"] >= 0
    route = (ARCHIVE / "implementation/route-status.rpt").read_text()
    assert re.search(r"nets with routing errors\.*\s*:\s+0", route)
    assert "checking unconstrained_internal_endpoints (0)" in timing
    cdc = (ARCHIVE / "implementation/cdc.rpt").read_text()
    assert not re.search(r"^CDC-\d+\s+Critical\s+\d+", cdc, re.MULTILINE)
    drc = (ARCHIVE / "implementation/drc.rpt").read_text()
    assert not re.search(
        r"^\|[^|\n]+\|\s*(?:Error|Critical Warning)\s*\|", drc, re.MULTILINE
    )

    hardware = read(ARCHIVE / "hardware/AUTOMATIC_BOOT_RESULT.json")
    assert hardware["result"] == "PASS_FLASH_PROGRAM_AND_AUTOMATIC_LINUX_BOOT"
    assert hardware["bitstream_sha256"] == record["bitstream_sha256"]
    assert hardware["packed_payload_sha256"] == packed["packed_payload_sha256"]
    assert hardware["flash_image_sha256"] == packed["flash_image_sha256"]
    assert hardware["backup_bytes"] == 16777216 and not hardware["backup_published"]
    for name, expected in hardware["evidence_sha256"].items():
        assert sha(ARCHIVE / "hardware" / name) == expected, name
    program = (ARCHIVE / "hardware/program.log").read_bytes()
    assert b"Program/Verify Operation successful." in program
    assert b"FLASH_BOOT_CONFIG_STATUS 01010000000100000111100111111100" in program

    cold = read(ARCHIVE / "hardware/cold-boot-1.json")
    assert cold["result"] == "PASS_FLASH_LINUX" and cold["exit_status"] == 0
    assert cold["disconnect_required"] and cold["usb_disconnections"] >= 1
    assert record["operator_confirmed_all_power_removed"]
    assert record["physical_cold_boot_tested"] and not record["board_release_ready"]
    assert set(cold["checks"]) == {"PASS " + check for check in CHECKS}
    for name in ("linux-console.log", "cold-boot-1.log"):
        data = (ARCHIVE / "hardware" / name).read_bytes()
        assert b"PASS FLASH_PAYLOAD_CRC" in data and b"OpenSBI v1.9" in data
        assert b"Linux version 6.6.0" in data and b"Kernel panic" not in data
        assert re.search(rb"(?:^|\n)FLASH_LINUX_RC:0\r*\n", data)
        for check in CHECKS:
            assert ("PASS " + check).encode() in data
    assert (
        b"OBSERVER_USB_DISCONNECTED"
        in (ARCHIVE / "hardware/cold-boot-1.log").read_bytes()
    )
    assert read(ARCHIVE / "tests/flash-regression/RESULT.json")["result"] == "PASS"
    recovery = read(ARCHIVE / "tests/board-uart-flash-recovery/RESULT.json")
    assert recovery["result"] == "PASS_UART_LOAD_VERIFY_BOOT"
    assert recovery["flash_rom_recovery"] and recovery["bytes_verified"] == 110592
    assert (
        not recovery["preloaded_ddr_image"]
        and not recovery["testbench_cpu_release_override"]
    )
    assert read(ARCHIVE / "tests/board-unit/RESULT.json")["result"] == "PASS"
    print(
        "PASS Flash evidence: implementation, program/verify and physical cold-start Linux checks"
    )


if __name__ == "__main__":
    verify()
