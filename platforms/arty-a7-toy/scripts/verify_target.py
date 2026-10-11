"""Verify published sources/evidence and, optionally, the regenerated core."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from verify_hardware_evidence import verify as verify_hardware

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/2026-10-11"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", action="store_true")
    args = parser.parse_args()
    lock = read(ROOT / "SOURCE_LOCK.json")
    for name, expected in lock["files"].items():
        assert sha(ROOT / name) == expected, name
    reference = read(ROOT / "tests/REFERENCE_MANIFEST.json")
    for name, expected in reference["files"].items():
        assert sha(ROOT / "tests/reference" / name) == expected, name
    vendor = read(ROOT / "board/vendor/MANIFEST.json")
    for name, spec in vendor["files"].items():
        assert sha(ROOT / "board/vendor" / name) == spec["sha256"], name
    record = read(EVIDENCE / "BOARD_RESULT.json")
    assert record["result"] == "PASS_BOARD_IMPLEMENTATION_AND_RTL_REGRESSIONS"
    assert record["part"] == "xc7a100tcsg324-1"
    assert record["core_rtl_sha256"] == lock["core_rtl_sha256"]
    assert record["gemmini_mesh_dsp"] == 64
    # This immutable October 11 record predates the separate physical archive.
    assert not record["physical_linux_boot_tested"] and not record["board_release_ready"]
    for name, expected in record["board_sources"].items():
        if not name.endswith(".md"):
            assert sha(ROOT / name) == expected, name
    area = {}
    labels = {"Slice LUTs": "LUT", "Slice Registers": "FF", "Block RAM Tile": "BRAM_tiles",
              "DSPs": "DSP", "Slice": "Slice"}
    for line in (EVIDENCE / "implementation/routed-utilization.rpt").read_text().splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) > 3 and fields[1] in labels:
            area[labels[fields[1]]] = float(fields[2])
    for name, value in area.items():
        assert value == record["routed_resources"][name], name
    assert set(area) == set(labels.values())
    assert record["timing"]["wns_ns"] >= 0 and record["timing"]["whs_ns"] >= 0
    assert all(row["severity"] != "Critical" for row in record["cdc"])
    assert "nets with routing errors" in record["route_status"]
    assert record["route_status"]["nets with routing errors"] == 0
    transcript = (EVIDENCE / "tests/linux-final/simulation.log").read_text()
    for marker in record["linux"]["checks"]:
        assert marker in transcript, marker
    assert re.search(r"PASS BOARD_LINUX_USERSPACE cycles=273506752", transcript)
    assert read(EVIDENCE / "tests/uart-boot/RESULT.json")["result"] == "PASS_UART_LOAD_VERIFY_BOOT"
    verify_hardware()
    if args.core:
        assert sha(ROOT / "build/serial-bound/ToyLinuxChip.sv") == lock["core_rtl_sha256"]
        assert sha(ROOT / "build/serial-bound/FpgaMemories.sv") == lock["memory_rtl_sha256"]
        upstream = read(ROOT / "UPSTREAM_MANIFEST.json")
        for name, metadata in upstream["files"].items():
            assert sha(ROOT / "upstream" / name) == metadata["sha256"], name
    print(f"PASS Toy target: {len(lock['files'])} source hashes; published implementation and RTL evidence")
    if args.core:
        print("PASS regenerated Chisel core and FPGA memory/RF binding match the validated bytes")


if __name__ == "__main__":
    main()
