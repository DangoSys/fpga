"""在全新隔离目录按原 bbkernel 流程构建 Linux/Gemmini 测试镜像。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-base", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    baseline = json.loads((ROOT / "SOFTWARE_BASELINE.json").read_text())
    cache = ROOT / "build/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    for name, commit in baseline.items():
        filename = f"{name}-{commit}.tar.gz"
        source = args.cache_base / "build/downloads" / filename
        target = cache / filename
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
            print(f"CACHE {name} {digest(target)}", flush=True)
    environment = os.environ.copy()
    environment["PATH"] = str(args.sdk / "bin") + ":" + environment["PATH"]

    def run(command, timeout):
        print("RUN " + " ".join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), cwd=ROOT, env=environment,
                       timeout=timeout, check=True)

    run(["python3", "software/prepare_gemmini_linux.py"], 60)
    run(["cmake", "-S", "build/linux-gemmini", "-B", "build/linux-gemmini-build",
         "-DCMAKE_C_COMPILER=riscv64-unknown-linux-gnu-gcc"], 60)
    run(["cmake", "--build", "build/linux-gemmini-build", "-j8"], 180)
    workloads = ROOT / "build/software/bb-tests/output/workloads"
    run(["cmake", "--install", "build/linux-gemmini-build", "--prefix", workloads], 60)
    # Existing entry installs the Linux system check, builds rootfs and Linux,
    # and packages the original OpenSBI firmware. No alternate runtime uploader.
    run(["bash", "software/build.sh"], 2400)
    run(["python3", "scripts/build_board_firmware.py",
         "--cross-compile", "riscv64-unknown-linux-gnu-"], 300)
    payload = ROOT / "build/board-software/fw_payload.bin"
    prepared = json.loads((ROOT / "build/linux-gemmini/PREPARED.json").read_text())
    installed = sorted(workloads.glob("*-linux"))
    rootfs = ROOT / "build/software/kernel-build/rootfs/root"
    if len(installed) != 15:
        raise RuntimeError(f"Expected 15 workloads, got {len(installed)}")
    for path in installed:
        if digest(path) != digest(rootfs / path.name):
            raise RuntimeError(f"Rootfs workload mismatch: {path.name}")
    result = {
        "result": "PASS_BUILD_NOT_HARDWARE_TESTED",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "software_baseline": baseline,
        "profile": prepared["profile"],
        "payload_bytes": payload.stat().st_size,
        "payload_sha256": digest(payload),
        "workloads": {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                      for path in installed},
        "rootfs_install_verified": True,
        "flash_modified": False,
        "hardware_gemmini_tested": False,
        "model_end_to_end_tested": False,
    }
    (ROOT / "build/LINUX_GEMMINI_BUILD.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
