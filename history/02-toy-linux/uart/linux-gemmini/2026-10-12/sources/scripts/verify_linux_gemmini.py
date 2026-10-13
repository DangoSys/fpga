"""离线核验标准镜像与实物日志；仅从实际 PASS 行汇总计算耗时。"""

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SHAPES = [(8, 8, 8), (16, 16, 16), (13, 11, 17), (8, 24, 8)]
CHECKS = [
    "VM_COPY_ON_WRITE",
    "VM_PAGE_PROTECTION",
    "FP64_PROCESS_CONTEXT",
    "LINUX_TIMER",
    "LINUX_SYSTEM_CHECK",
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--hardware-result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build = read(args.build_record)
    result = read(args.hardware_result)
    original = read(ROOT / "evidence/2026-10-11/BOARD_RESULT.json")
    require(build["result"] == "PASS_BUILD_NOT_HARDWARE_TESTED", "Build did not pass")
    require(result["result"] == "PASS_LINUX_AND_GEMMINI_HARDWARE", "Hardware did not pass")
    require(result["bitstream_sha256"] == original["bitstream_sha256"], "Wrong bitstream")
    require(result["payload_sha256"] == build["payload_sha256"], "Payload mismatch")
    require(result["ddr_readback_bytes"] == build["payload_bytes"], "Incomplete DDR readback")
    require(not result["flash_written"], "Expected temporary deployment")
    require(result["elapsed_seconds"] < result["timeout_seconds"] == 3600, "Invalid timeout")
    require(len(result["tests"]) == result["test_count"] == 15, "Expected 15 workloads")
    tests = {item["name"]: item for item in result["tests"]}
    require(set(tests) == set(build["workloads"]), "Workload set mismatch")
    raw = (args.hardware_result.parent / "linux-console.log").read_bytes()
    console = raw.replace(b"\r", b"").decode(errors="replace")
    boot_file = args.hardware_result.parent / "boot-console.log"
    boot = boot_file.read_bytes().decode(errors="replace") if boot_file.is_file() else console
    require("OpenSBI v1.9" in boot and "Linux version 6.6.0" in boot, "Wrong boot")
    if result.get("configuration_reused"):
        load = read(args.hardware_result.parent / "LOAD_RESULT.json")
        require(load["payload_sha256"] == build["payload_sha256"]
                and load["bitstream_sha256"] == result["bitstream_sha256"]
                and load["ddr_readback_bytes"] == build["payload_bytes"], "Wrong prior load")
        expected_hashes = {name: item["sha256"] for name, item in build["workloads"].items()}
        require(result["workload_hashes"] == expected_hashes, "Live workload hash mismatch")
        for name, expected in expected_hashes.items():
            require(re.search(rf"^{expected}\s+/root/{re.escape(name)}$",
                              console, re.MULTILINE), "Missing raw live hash: " + name)
    require("Kernel panic" not in console, "Kernel panic in transcript")
    for index, item in enumerate(result["tests"]):
        require(item["exit_code"] == 0, "Failed workload: " + item["name"])
        require(item["output"] in console, "Structured output differs from raw transcript")
        require(re.search(rf"^WB_TEST_RC_{index}:0$", console, re.MULTILINE),
                "Missing raw process return code: " + item["name"])
    for label in CHECKS:
        require("PASS " + label in tests["linux_system_check-linux"]["output"], label)
    sources = ROOT / "tests/reference/examples/balls/gemmini/workloads/ctests"
    for source in sources.glob("*.c"):
        output = tests[source.stem + "-linux"]["output"]
        markers = re.findall(r'printf\("([^"\n]* PASSED)\\n"\)',
                             source.read_text(encoding="utf-8"))
        require(len(markers) == 1 and markers[0] in output, "Missing oracle: " + source.name)
        require(markers[0] in console, "Missing raw oracle: " + source.name)
    output = tests["gemmini_linux_check-linux"]["output"]
    pattern = (r"^PASS GEMMINI_CASE id=(\d+) mode=(OS|WS) m=(\d+) n=(\d+) k=(\d+) "
               r"cpu_ns=(\d+) accelerator_end_to_end_ns=(\d+)$")
    rows = re.findall(pattern, output, re.MULTILINE)
    require(len(rows) == result["blocked_matmul_cases"] == 16, "Missing matrix cases")
    measurements = []
    for index, row in enumerate(rows):
        case, mode, m, n, k, cpu, accelerator = row
        shape = tuple(map(int, (m, n, k)))
        require(int(case) == index + 1 and shape == SHAPES[(index % 8) // 2]
                and mode == ("WS" if index % 2 else "OS"), "Wrong case order/shape")
        require(int(cpu) > 0 and int(accelerator) > 0, "Unusable timing sample")
        require("PASS GEMMINI_CASE " + " ".join([
            f"id={case}", f"mode={mode}", f"m={m}", f"n={n}", f"k={k}",
            f"cpu_ns={cpu}", f"accelerator_end_to_end_ns={accelerator}",
        ]) in console, "Missing raw matrix result")
        measurements.append({
            "case": int(case), "mode": mode, "m": int(m), "n": int(n), "k": int(k),
            "cpu_ns": int(cpu), "accelerator_end_to_end_ns": int(accelerator),
            "cpu_over_accelerator": round(int(cpu) / int(accelerator), 4),
        })
    require("PASS GEMMINI_LINUX_CHECK cases=16" in output, "Missing final oracle")
    require("PASS GEMMINI_LINUX_CHECK cases=16" in console, "Missing raw final oracle")
    summary = {
        "result": "PASS_OFFLINE_VERIFICATION",
        "console_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": build["payload_sha256"],
        "matrix_measurements": measurements,
        "timing_scope": "分块、DMA、配置、同步和 CPU 跨 K 累加；不是纯 MAC 延迟",
        "model_end_to_end_tested": False,
    }
    if args.output:
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print("PASS offline verification: 15 workloads, five Linux checks, 16 matrix cases")
    for item in measurements:
        print(f"CASE {item['case']:2} {item['mode']} {item['m']}x{item['n']}x{item['k']} "
              f"CPU={item['cpu_ns'] / 1e6:.3f}ms "
              f"accelerator={item['accelerator_end_to_end_ns'] / 1e6:.3f}ms "
              f"CPU/accelerator={item['cpu_over_accelerator']:.4f}")


if __name__ == "__main__":
    main()
