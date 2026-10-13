"""临时烧录已验证位流、完整读回标准镜像，运行 Linux/Gemmini 测试并归档证据。"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
import uuid

from ftdi_transport import D2xxPort
from load import Loader

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BIT = "9f6f684361c049527fda09818cc8aa464f1067b75f3762305a27c5c738295942"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded_command(program, marker, seconds=90):
    # $! and $? produce numeric values. Wait for both children so the watcher
    # cannot retain a pending job/zombie after a successful workload.
    command = (f"{program} & p=$!; (sleep {seconds}; kill -KILL $p) & w=$!; "
               f"wait $p; r=$?; kill $w 2>/dev/null; wait $w 2>/dev/null; "
               f"printf '\\n{marker}:%s\\n' $r\n")
    if len(command.encode()) >= 220:
        raise ValueError("Console command exceeds the RX FIFO budget")
    return command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--build-result", type=Path, required=True)
    parser.add_argument("--bitstream", type=Path, required=True)
    parser.add_argument("--vivado", type=Path, required=True)
    parser.add_argument("--port", default="COM5")
    parser.add_argument("--expected-bit-sha256", default=EXPECTED_BIT,
                        help="重建 UART 位流后，填写已通过实现检查的位流 SHA256")
    parser.add_argument("--loaded-run", type=Path,
                        help="继续完整读回且已启动 Linux 的运行；逐个核验板上程序摘要")
    args = parser.parse_args()
    build = json.loads(args.build_result.read_text(encoding="utf-8"))
    if build["result"] != "PASS_BUILD_NOT_HARDWARE_TESTED":
        raise ValueError("Expected a verified standard-image build record")
    expected_bit = args.expected_bit_sha256.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_bit):
        raise ValueError("Expected an explicit 64-digit bitstream SHA256")
    if digest(args.payload) != build["payload_sha256"] or digest(args.bitstream) != expected_bit:
        raise ValueError("Payload or previously validated UART bitstream hash mismatch")
    out = ROOT / "build" / ("hardware-gemmini-" + time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"result": "RUNNING", "bitstream_sha256": expected_bit,
              "payload_sha256": build["payload_sha256"], "port": args.port,
              "timeout_seconds": 3600, "flash_written": False, "tests": []}
    try:
        if args.loaded_run:
            previous = json.loads((args.loaded_run / "RESULT.json").read_text(encoding="utf-8"))
            boot = (args.loaded_run / "linux-console.log").read_bytes()
            if (previous["bitstream_sha256"] != expected_bit
                    or previous["payload_sha256"] != build["payload_sha256"]
                    or previous.get("ddr_readback_bytes") != build["payload_bytes"]
                    or b"Linux version 6.6.0" not in boot or b"~ # " not in boot
                    or b"Kernel panic" in boot or previous["flash_written"]):
                raise ValueError("Loaded run lacks complete DDR/boot evidence")
            shutil.copy2(args.loaded_run / "RESULT.json", out / "LOAD_RESULT.json")
            shutil.copy2(args.loaded_run / "linux-console.log", out / "boot-console.log")
            for name in ["program.log", "program.jou", "program-console.log"]:
                shutil.copy2(args.loaded_run / name, out / name)
            result["loaded_run"] = str(args.loaded_run.resolve())
            result["ddr_readback_bytes"] = previous["ddr_readback_bytes"]
            result["ddr_transfer_seconds"] = previous["ddr_transfer_seconds"]
            result["configuration_reused"] = True
            print("REUSE COMPLETE_DDR_READBACK_AND_LINUX_BOOT", flush=True)
        else:
            with (out / "program-console.log").open("wb") as log:
                subprocess.run([str(args.vivado), "-mode", "batch", "-source",
                                str(ROOT / "program.tcl"), "-log", str(out / "program.log"),
                                "-journal", str(out / "program.jou"), "-tclargs", str(args.bitstream.resolve())],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
            print("PASS VOLATILE_JTAG_PROGRAM", flush=True)
        data = args.payload.read_bytes()
        with D2xxPort(args.port, timeout_seconds=3500) as port:
            if not args.loaded_run:
                loader = Loader(port)
                info = loader.request(4)
                if info != b"TA7\x02" + struct.pack("<II", 268435456, 25000000):
                    raise RuntimeError("Unexpected board DDR loader profile")
                print("PASS LOADER_INFO DDR=256MiB CPU=25MHz", flush=True)
                transfer_start = time.monotonic()
                for offset in range(0, len(data), 256):
                    if time.monotonic() - started > 3500:
                        raise TimeoutError("One-hour board verification timeout")
                    chunk = data[offset:offset + 256]
                    loader.request(1, 0x80000000 + offset, len(chunk), chunk)
                    if loader.request(2, 0x80000000 + offset, len(chunk)) != chunk:
                        raise RuntimeError(f"DDR readback mismatch at {offset:#x}; CPU remains reset")
                    if offset % 1048576 == 0:
                        print(f"DDR_VERIFY {offset + len(chunk)}/{len(data)}", flush=True)
                result["ddr_readback_bytes"] = len(data)
                result["ddr_transfer_seconds"] = round(time.monotonic() - transfer_start, 3)
                print(f"PASS FULL_DDR_READBACK bytes={len(data)} seconds={result['ddr_transfer_seconds']}", flush=True)
                loader.request(3, 0x80000000)
            with (out / "linux-console.log").open("wb") as log:
                console = bytearray()

                def read_until(pattern, seconds):
                    deadline = time.monotonic() + seconds
                    while time.monotonic() < deadline:
                        block = port.read(4096)
                        if block:
                            console.extend(block)
                            log.write(block)
                            log.flush()
                            if b"Kernel panic" in console:
                                raise RuntimeError("Kernel panic; inspect raw console")
                            match = re.search(pattern, console)
                            if match:
                                return match
                    raise TimeoutError("Linux console response timeout; inspect raw transcript")

                if args.loaded_run:
                    marker = "WB_RESUME_" + out.name.rsplit("-", 1)[-1]
                    port.write(f"\nprintf '{marker}\\n'\n".encode())
                    read_until(rb"(?:^|\n)" + marker.encode() + rb"\r*\n", 15)
                    result["workload_hashes"] = {}
                    for index, (name, metadata) in enumerate(build["workloads"].items()):
                        console.clear()
                        marker = f"WB_HASH_{index}"
                        port.write((f"/bin/busybox sha256sum /root/{name}; "
                                    f"printf '\\n{marker}:%s\\n' \"$?\"\n").encode())
                        match = read_until(rb"(?:^|\n)" + marker.encode() + rb":(\d+)\r*\n", 60)
                        if int(match.group(1)) or not re.search(
                                rb"(?:^|\n)" + metadata["sha256"].encode() + rb"\s+/root/"
                                + re.escape(name.encode()) + rb"\r*\n", console):
                            raise RuntimeError("Live rootfs workload hash mismatch: " + name)
                        result["workload_hashes"][name] = metadata["sha256"]
                        print("PASS LIVE_WORKLOAD_SHA256 " + name, flush=True)
                else:
                    read_until(rb"~ # ", 180)
                    if b"Linux version 6.6.0" not in console:
                        raise RuntimeError("Expected real Linux 6.6.0 boot")
                    print("PASS LINUX_BOOT", flush=True)
                commands = ["linux_system_check-linux", "gemmini_linux_check-linux"]
                commands += sorted(name for name in build["workloads"]
                                   if name not in commands)
                for index, name in enumerate(commands):
                    console.clear()
                    marker = f"WB_TEST_RC_{index}"
                    command = bounded_command("/root/" + name, marker)
                    print("RUN " + name, flush=True)
                    port.write(command.encode())
                    match = read_until(rb"(?:^|\n)" + marker.encode() + rb":(\d+)\r*\n", 120)
                    code = int(match.group(1))
                    output = bytes(console).replace(b"\r", b"").decode(errors="replace")
                    item = {"name": name, "exit_code": code, "output": output}
                    result["tests"].append(item)
                    print(output, flush=True)
                    if code or (name == "gemmini_linux_check-linux" and "PASS GEMMINI_LINUX_CHECK cases=16" not in output):
                        raise RuntimeError(f"Hardware workload failed: {name} rc={code}")
                    if name == "linux_system_check-linux":
                        for label in ["VM_COPY_ON_WRITE", "VM_PAGE_PROTECTION",
                                      "FP64_PROCESS_CONTEXT", "LINUX_TIMER", "LINUX_SYSTEM_CHECK"]:
                            if "PASS " + label not in output:
                                raise RuntimeError("Missing Linux check: " + label)
                result["result"] = "PASS_LINUX_AND_GEMMINI_HARDWARE"
                result["test_count"] = len(result["tests"])
                result["blocked_matmul_cases"] = 16
    except BaseException as error:
        result["result"] = "FAIL"
        result["error"] = str(error)
        raise
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("RESULT " + str(out / "RESULT.json"), flush=True)


if __name__ == "__main__":
    main()
