"""生成匹配实际 8×8 核心的 Linux 测试构建输入，不执行编译。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path,
                        default=ROOT / "evidence/2026-10-13/rob-pr10-full/ToyLinuxChip.profile.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/linux-gemmini")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    expected = {"gemmini_rows": 8, "gemmini_columns": 8, "bank_width": 64,
                "bank_count": 8, "virtual_bank_count": 16, "bank_rows": 1024}
    for key, value in expected.items():
        if profile[key] != value:
            raise ValueError(f"Wrong hardware profile: {key}={profile[key]}, expected {value}")
    reference = ROOT / "tests/reference"
    manifest = json.loads((ROOT / "tests/REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        if hashlib.sha256((reference / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Changed pinned reference: {name}")
    out = args.output.resolve()
    if out == ROOT or out in ROOT.parents:
        raise ValueError("Output must not replace the source directory")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(reference, out / "reference", dirs_exist_ok=True)
    shutil.copy2(ROOT / "software/gemmini_linux_check.c", out / "gemmini_linux_check.c")
    (out / "params.h").write_text(
        "#define BANK_WIDTH 64\n#define PHYSICAL_BANK_NUM 8\n"
        "#define VIRTUAL_BANK_NUM 16\n#define BANK_ENTRIES 1024\n#define GEMMINI_DIM 8\n",
        encoding="utf-8")
    # Preserve the exact pinned Gemmini instruction encodings; do not use
    # upstream Berkeley Gemmini binaries with this Buckyball instruction ABI.
    names = {2: "CONFIG", 3: "FLUSH", 53: "PRELOAD", 66: "COMPUTE_PRELOADED",
             67: "COMPUTE_ACCUMULATED", 80: "LOOP_WS_CONFIG_BOUNDS",
             81: "LOOP_WS_CONFIG_ADDR_A", 82: "LOOP_WS_CONFIG_ADDR_B",
             83: "LOOP_WS_CONFIG_ADDR_D", 84: "LOOP_WS_CONFIG_ADDR_C",
             85: "LOOP_WS_CONFIG_STRIDES_AB", 86: "LOOP_WS_CONFIG_STRIDES_DC",
             87: "LOOP_WS"}
    names.update({95 + index: f"LOOP_CONV_WS_CONFIG_{index}" for index in range(1, 10)})
    names[105] = "LOOP_CONV_WS"
    if set(names) != set(profile["ball_funct7"]):
        raise ValueError("Instruction definitions do not match the emitted profile")
    (out / "ballISA.h").write_text("\n".join(
        f"#define BB_FUNC7_GEMMINI_{name} {number}" for number, name in names.items()) + "\n",
        encoding="utf-8")
    sources = []
    for index, original in enumerate(sorted((reference / "examples/balls/gemmini/workloads/ctests").glob("*.c")), 1):
        data = original.read_text(encoding="utf-8")
        if data.count("#define DIM 16") != 1:
            raise ValueError(f"Unexpected test dimension: {original}")
        target = out / (original.stem + ".c")
        target.write_text(data.replace("#define DIM 16", "#define DIM 8"), encoding="utf-8")
        sources.append(target.name)
    cmake = '''cmake_minimum_required(VERSION 3.22)
project(ToyLinuxGemmini C)
set(CMAKE_C_STANDARD 11)
add_compile_options(-march=rv64gc -mabi=lp64d -O2 -Wall -Wextra -Werror -ffp-contract=off)
add_link_options(-static)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}
  reference/bb-tests/workloads/lib reference/examples/balls/gemmini/workloads)
add_library(bb_reference STATIC reference/bb-tests/workloads/lib/buckyball.c
  reference/bb-tests/workloads/lib/bbhw/mem/mem.c
  reference/bb-tests/workloads/lib/bbhw/isa/isa.c)
set(workloads gemmini_linux_check-linux)
add_executable(gemmini_linux_check-linux gemmini_linux_check.c)
target_link_libraries(gemmini_linux_check-linux PRIVATE bb_reference m)
'''
    for name in sources:
        target = Path(name).stem + "-linux"
        cmake += f"add_executable({target} {name})\ntarget_link_libraries({target} PRIVATE bb_reference m)\nlist(APPEND workloads {target})\n"
    cmake += "install(TARGETS ${workloads} RUNTIME DESTINATION .)\n"
    (out / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
    (out / "PREPARED.json").write_text(json.dumps({
        "result": "PREPARED_NOT_BUILT", "dimension": 8,
        "reference_commit": manifest["commit"], "original_cases": sources,
        "new_blocked_matmul_cases": 16, "profile": expected,
        "model_end_to_end_tested": False,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(sources)} pinned cases and one blocked-matmul workload in {out}")


if __name__ == "__main__":
    main()
