"""离线核验本次实物归档的文件、输入、DDR/启动片段和超时保护证据。"""

import hashlib
import json
from pathlib import Path
import re

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = evidence_path("2026-10-12/linux-gemmini")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read(ARCHIVE / "MANIFEST.json")
    for name, metadata in manifest["files"].items():
        path = (ARCHIVE / name).resolve()
        require(path.is_relative_to(ARCHIVE.resolve()), "Invalid archive path")
        require(sha(path) == metadata["sha256"], "Archive hash mismatch: " + name)
    inputs = read(ARCHIVE / "build/INPUT_MANIFEST.json")
    for name, metadata in inputs["source_files"].items():
        snapshot = ARCHIVE / "sources" / name
        path = (snapshot if snapshot.is_file() else
                evidence_path(name[len("evidence/"):]) if name.startswith("evidence/") else ROOT / name)
        require(sha(path) == metadata["sha256"], "Source binding mismatch: " + name)
    for name, metadata in inputs["generated_build_inputs"].items():
        require(sha(ARCHIVE / "generated-inputs" / name) == metadata["sha256"], name)
    for original in (ROOT / "tests/reference/examples/balls/gemmini/workloads/ctests").glob("*.c"):
        expected = original.read_text(encoding="utf-8").replace("#define DIM 16", "#define DIM 8")
        actual = (ARCHIVE / "generated-inputs" / original.name).read_text(encoding="utf-8")
        require(actual == expected, "Reference oracle changed: " + original.name)
    load = read(ARCHIVE / "load/RESULT.json")
    build = read(ARCHIVE / "build/LINUX_GEMMINI_BUILD.json")
    require(load["result"] == "PASS_DDR_READBACK_AND_LINUX_BOOT", "Load stage did not pass")
    require(load["ddr_readback_bytes"] == build["payload_bytes"], "Incomplete DDR image")
    transfer = (ARCHIVE / "load/transfer.log").read_bytes()
    marker = f"PASS FULL_DDR_READBACK bytes={build['payload_bytes']} seconds={load['ddr_transfer_seconds']}"
    require(marker.encode() in transfer, "Missing full readback proof")
    require(b"PASS LINUX_BOOT" in transfer, "Missing boot checkpoint")
    boot = (ARCHIVE / "load/linux-boot.log").read_bytes()
    require(b"OpenSBI v1.9" in boot and b"Linux version 6.6.0" in boot and b"~ # " in boot,
            "Missing physical Linux boot")
    for directory in ["hardware", "first-pass"]:
        require(read(ARCHIVE / directory / "LOAD_RESULT.json") == load, "Different reused load")
        require((ARCHIVE / directory / "boot-console.log").read_bytes() == boot, "Different boot prefix")
    watchdog = read(ARCHIVE / "watchdog/RESULT.json")
    require(watchdog["result"] == "PASS_WATCHDOG_SUCCESS_FAILURE_TIMEOUT_AND_REAP", "Watchdog failed")
    require([row["exit_code"] for row in watchdog["cases"]] == [0, 1, 137], "Wrong exit cases")
    console = (ARCHIVE / "watchdog/check.log").read_bytes()
    for index, row in enumerate(watchdog["cases"]):
        require(row["watcher_alive_rc"] == 1, "Watcher not reaped")
        require(re.search(rb"(?:^|\n)WATCH_SELF_" + str(index).encode() + rb":"
                          + str(row["exit_code"]).encode() + rb"\r*\n", console), "Missing exit proof")
        require(re.search(rb"(?:^|\n)WATCH_REAP_" + str(index).encode() + rb":1\r*\n", console),
                "Missing reap proof")
    post = read(ARCHIVE / "hardware/POST_RESULT.json")
    require(post["result"] == "PASS_POST_TEST_LIVE_SHELL" and post["watchdog_alive_rc"] == 1,
            "Post-test shell/reap check failed")
    require(post["uart_latency_restored_ms"] == 16 and not post["flash_written"], "Wrong cleanup")
    require(not manifest["flash_written"] and not manifest["model_end_to_end_tested"], "Wrong scope")
    print(f"PASS Linux/Gemmini archive: {len(manifest['files'])} files, pinned inputs, DDR/boot and watchdog")


if __name__ == "__main__":
    main()
