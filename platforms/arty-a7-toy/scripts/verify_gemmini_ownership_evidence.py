"""核验设备所有权候选的离线档案，不授予实板资格。"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "evidence/2026-10-13/gemmini-ownership"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args()
    manifest = read(ARCHIVE / "MANIFEST.json")
    for name, digest in manifest["files"].items():
        assert sha(ARCHIVE / name) == digest, name
    inputs = read(ARCHIVE / "INPUTS.json")
    assert not inputs["hardware_changed"] and not inputs["hardware_tested"]
    assert not inputs["dma_context_isolation_proven"]
    for name, digest in inputs["software_sources"].items():
        assert sha(ARCHIVE / "sources" / name) == digest, name
    assert sha(ARCHIVE / "teammate-concurrency.log") == inputs["teammate_log_sha256"]
    host = read(ARCHIVE / "HOST_RESULT.json")
    assert host["result"] == "PASS_HOST_SOFTWARE_ONLY" and host["cases"] == 14
    assert host["concurrency"] == {"processes": 6, "transactions": 120, "overlap": 0}
    assert host["board_controller_backend"] == "native_mock_not_hardware"
    assert not host["hardware_tested"] and not host["dma_context_isolation_proven"]
    for name, digest in host["sources"].items():
        assert sha(ARCHIVE / "sources" / name) == digest, name
    build = read(ARCHIVE / "LINUX_GEMMINI_BUILD.json")
    assert build["result"] == "PASS_BUILD_NOT_HARDWARE_TESTED"
    assert len(build["workloads"]) == 15 and len(build["ownership_link_verified"]) == 14
    expected = set(build["workloads"]) - {"linux_system_check-linux"}
    assert set(build["ownership_link_verified"]) == expected
    assert build["rootfs_install_verified"] and build["linux_file_locking_enabled"]
    assert not build["hardware_gemmini_tested"] and not build["flash_modified"]
    assert not build["gemmini_ownership"]["hardware_context_isolation_proven"]
    for name, digest in build["build_inputs"].items():
        assert sha(ARCHIVE / "generated-inputs" / name) == digest, name
    script = ARCHIVE / "sources/software/runtime/gemmini_concurrency.sh"
    assert sha(script) == build["rootfs_helpers"][script.name]["sha256"]
    assert "CONFIG_FILE_LOCKING=y\n" in (ARCHIVE / "audit/linux.config").read_text()
    session = read(ARCHIVE / "SESSION.json")
    assert session["exit_code"] == 0 and session["timeout_seconds"] == 3600
    if args.payload:
        assert args.payload.stat().st_size == build["payload_bytes"]
        assert sha(args.payload) == build["payload_sha256"]
    print(f"PASS Gemmini ownership offline archive: {len(manifest['files'])} hashes; hardware_tested=false")


if __name__ == "__main__":
    main()
