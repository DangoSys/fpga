"""核验 ROB RAM 候选档案；实物资格不从旧版本继承。"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = evidence_path("2026-10-12/rob-ram")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resources(path):
    labels = {"Slice LUTs": "LUT", "Slice Registers": "FF", "Slice": "Slice",
              "Block RAM Tile": "BRAM_tiles", "DSPs": "DSP"}
    values = {}
    for line in path.read_text().splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) > 3 and fields[1] in labels:
            values[labels[fields[1]]] = float(fields[2])
    assert set(values) == set(labels.values())
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", action="store_true")
    args = parser.parse_args()
    manifest = read(ARCHIVE / "MANIFEST.json")
    for name, expected in manifest["files"].items():
        assert sha(ARCHIVE / name) == expected, name
    record = read(ARCHIVE / "RESULT.json")
    assert record["result"] == "PASS_ROB_RAM_RTL_AND_BOARD_IMPLEMENTATION"
    assert record["physical_board_tested"] is False
    assert record["flash_boot_tested"] is False
    run = read(ARCHIVE / "implementation/RUN.json")
    assert run["status"] == "COMPLETED" and run["exit_code"] == 0
    assert run["bitstream_generated"] and run["timeout_seconds"] == 3600
    assert run["candidate_core_unchanged"] and run["candidate_memory_unchanged"]
    assert resources(ARCHIVE / "implementation/routed-utilization.rpt") == record["routed_resources"]
    before = read(evidence_path("2026-10-11/BOARD_RESULT.json"))["routed_resources"]
    for name, value in record["routed_resources"].items():
        assert value - before[name] == record["resource_delta"][name], name
    assert read(ARCHIVE / "ToyLinuxChip.profile.json") == read(
        evidence_path("2026-10-11/ToyLinuxChip.profile.json"))
    assert read(ARCHIVE / "tests/globalrob/RESULT.json")["result"] == "PASS"
    assert "PASS all memory bindings" in (ARCHIVE / "tests/rob-memory-regression.log").read_text()
    regressions = read(ARCHIVE / "tests/BOARD_REGRESSION.json")
    baseline = read(evidence_path("2026-10-11/tests/BOARD_REGRESSION.json"))
    assert regressions["result"] == "PASS"
    for name, case in regressions["tests"].items():
        assert case["result"] == "PASS"
        assert case["cycles"] == baseline["tests"][name]["cycles"]
        assert case["binary_sha256"] == baseline["tests"][name]["binary_sha256"]
    linux = read(ARCHIVE / "tests/linux-final/RESULT.json")
    assert linux["result"] == "PASS_RTL_LINUX_USERSPACE" and not linux["physical_board_tested"]
    transcript = (ARCHIVE / "tests/linux-final/simulation.log").read_text()
    for marker in linux["checks"]:
        assert marker in transcript, marker
    assert "PASS BOARD_LINUX_USERSPACE cycles=273506752" in transcript
    timing = (ARCHIVE / "implementation/routed-timing.rpt").read_text()
    assert "All user specified timing constraints are met." in timing
    rows = timing.split("WNS(ns)", 1)[1].splitlines()
    values = next(line.split() for line in rows if re.match(r"\s+-?\d+\.\d+", line))
    assert float(values[0]) == record["timing"]["wns_ns"] >= 0
    assert float(values[4]) == record["timing"]["whs_ns"] >= 0
    assert all(float(values[n]) == 0 for n in [1, 2, 5, 6, 9, 10])
    route = (ARCHIVE / "implementation/route-status.rpt").read_text()
    assert re.search(r"nets with routing errors\.+\s*:\s*0\s*:", route)
    for name in ["drc.rpt", "cdc.rpt"]:
        assert not re.search(r"\b(?:Critical|Error)\b", (ARCHIVE / "implementation" / name).read_text())
    assert read(ARCHIVE / "OPTIN_RESULT.json")["result"] == "PASS_DEFAULT_AND_CANDIDATE_BYTE_IDENTITY"
    memory = read(ARCHIVE / "MEMORY_MANIFEST.json")
    assert memory["core_rtl_sha256"] == record["core_rtl_sha256"] == run["core_sha256"]
    assert memory["memory_rtl_sha256"] == record["memory_rtl_sha256"] == run["memory_sha256"]
    for name, expected in record["integration_sources"].items():
        assert sha(ARCHIVE.parent / "integration-inputs" / name) == expected, name
    if args.core:
        assert sha(ROOT / "build/serial-bound/ToyLinuxChip.sv") == record["core_rtl_sha256"]
        assert sha(ROOT / "build/serial-bound/FpgaMemories.sv") == record["memory_rtl_sha256"]
    print(f"PASS ROB RAM archive: {len(manifest['files'])} files; unchanged regression cycles; routed candidate")
    print("This initial archive predates physical tests; later hardware evidence is in PR #9")


if __name__ == "__main__":
    main()
