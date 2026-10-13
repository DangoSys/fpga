"""离线核验 PR #10 的不可变测试档案，不继承历史实物资格。"""

import hashlib
import json
from pathlib import Path

from history_paths import evidence_path

ARCHIVE = evidence_path("2026-10-12/pr10-review")


def read(name):
    return json.loads((ARCHIVE / name).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read("MANIFEST.json")
    for name, item in manifest["files"].items():
        data = (ARCHIVE / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item["sha256"], name)
        require(len(data) == item["bytes"], name)
    record = read("RESULT.json")
    require(record["result"] == "PASS_PR10_EVALUATION_AND_OFFLINE_REGRESSIONS", "review result")
    require(not any(record[key] for key in ["physical_hardware_tested", "new_bitstream_generated",
                                           "cpu_behavior_simulated", "physical_mig_simulated"]), "test scope")
    require(record["focused_patch_apply_check_exit_code"] == 0, "patch compatibility")
    require(len(record["comparison"]) == 5, "compared files")
    require(all(item["byte_identical"] and item["base_sha256"] == item["current_sha256"]
                for item in record["comparison"].values()), "old/current comparison")
    for name, expected in record["sources"].items():
        require(manifest["files"]["sources/" + name]["sha256"] == expected, name)
    require(manifest["files"]["old-platform.sv"]["sha256"] ==
            record["old_platform_expected_negative"]["source_sha256"], "old platform")
    board = read("board-unit/RESULT.json")
    require(board["result"] == "PASS" and board["tests"] == 4, "interface groups")
    ports = read("sources/tests/PLATFORM_PORTS_MANIFEST.json")
    require(not ports["cpu_behavior_included"], "CPU fixture scope")
    require(ports["stub_sha256"] == record["sources"]["tests/ToyLinuxChipPorts.sv"], "port fixture bytes")
    for directory, count in [("programming-check", 20), ("flash-guard-check", 10)]:
        cases = read(directory + "/RESULT.json")["cases"]
        require(len(cases) == count and all(case["result"] == "PASS" for case in cases), directory)
    negative = (ARCHIVE / "old-platform-negative.log").read_text()
    require("addr=60030000 actual=01 expected=10" in negative, "old RTL negative oracle")
    for name in ["program_arty.tcl", "backup_flash.tcl", "program_flash.tcl"]:
        log = (ARCHIVE / "original-pr" / (name + ".log")).read_text()
        require("MOCK_FAILURE expected boolean value" in log, name)
    print(f"PASS PR10 archive: {len(manifest['files'])} artifacts; 4/20/10 offline checks and expected negatives")
    verify_selfcheck()


def verify_selfcheck():
    archive = evidence_path("2026-10-13/pr10-selfcheck")

    def load(name):
        return json.loads((archive / name).read_text(encoding="utf-8"))

    manifest = load("MANIFEST.json")
    for name, item in manifest["files"].items():
        data = (archive / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item["sha256"] and len(data) == item["bytes"], name)
    record = load("RESULT.json")
    require(record["result"] == "PASS_PR10_SELFCHECK", "selfcheck result")
    require(not record["physical_hardware_tested"] and not record["new_bitstream_generated"], "selfcheck scope")
    for name, expected in record["sources"].items():
        require(manifest["files"]["sources/" + name]["sha256"] == expected, name)
    require(load("board-unit/RESULT.json")["tests"] == 4, "selfcheck interface groups")
    for directory, count in [("programming-check", 20), ("flash-guard-check", 10),
                             ("runner-status-check", 3), ("backpressure-mutation", 3)]:
        cases = load(directory + "/RESULT.json")["cases"]
        require(len(cases) == count and all(case["result"] == "PASS" for case in cases), directory)
    current = load("runner-status-check/RESULT.json")["cases"]
    require(all(case["exit_code"] != 0 and case["observed_result"] == "FAILED" for case in current), "fresh failures")
    old = load("stale-baseline/RESULT.json")["cases"]
    require(len(old) == 3 and all(case["exit_code"] != 0 and case["observed_result"].startswith("PASS")
                                for case in old), "stale baseline counterexamples")
    mutations = {case["case"]: case for case in load("backpressure-mutation/RESULT.json")["cases"]}
    require({name: case["exit_code"] for name, case in mutations.items()} ==
            {"old-test": 0, "new-test": 1, "old-response": 1}, "mutation outcomes")
    require("valid=0" in (archive / "backpressure-mutation/new-test.log").read_text(), "BVALID oracle")
    print(f"PASS PR10 selfcheck archive: {len(manifest['files'])} artifacts; fresh failure status and BVALID oracles")


if __name__ == "__main__":
    main()
