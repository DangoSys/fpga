"""只打包已通过完整实现/RTL 核验的 ROB/PR10 UART 工程预发布，不访问板卡。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from history_paths import evidence_path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def copy(source, root, name):
    destination = root / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def bind(root, kind, commit):
    record = {"flow": kind, "source_commit": commit, "target": "xc7a100tcsg324-1",
              "engineering_prerelease": True, "physical_hardware_tested_this_release": False,
              "files": {p.relative_to(root).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size}
                        for p in sorted(root.rglob("*")) if p.is_file()}}
    (root / "MANIFEST.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compress(root, output):
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                method = zipfile.ZIP_STORED if path.name.endswith(".tar.gz") else zipfile.ZIP_DEFLATED
                archive.write(path, path.relative_to(root).as_posix(), compress_type=method)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["bitstream", "payload", "core-dir", "validation", "os-inputs", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline-core", type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.validation.read_text())
    require(record["result"] == "PASS_ROB_PR10_FULL_VALIDATION", "完整验证尚未通过")
    require(not record["physical_hardware_tested"], "此入口只发布尚未实板测试的工程预发布")
    require(record["timing"]["wns_ns"] >= 0 and record["timing"]["whs_ns"] >= 0, "时序未通过")
    require(record["route_errors"] == record["critical_drc"] == record["critical_cdc"] == 0, "实现存在严重错误")
    for name, expected in [(args.bitstream, record["bitstream_sha256"]), (args.payload, record["payload_sha256"]),
                           (args.core_dir / "ToyLinuxChip.sv", record["core_rtl_sha256"]),
                           (args.core_dir / "FpgaMemories.sv", record["memory_rtl_sha256"])]:
        require(digest(name) == expected, "验证输入摘要不匹配：" + name.name)
    for name, expected in record["board_sources"].items():
        require(digest(ROOT / name) == expected, "板级源码已变：" + name)
    software = json.loads((evidence_path("2026-10-12/linux-gemmini/build/LINUX_GEMMINI_BUILD.json")).read_text())
    require(software["payload_sha256"] == record["payload_sha256"] and
            args.payload.stat().st_size == software["payload_bytes"], "软件镜像未匹配标准构建记录")
    inputs = json.loads((args.os_inputs / "INPUTS.json").read_text())
    for name, item in inputs.items():
        require(digest(args.os_inputs / name) == item["sha256"] and
                (args.os_inputs / name).stat().st_size == item["bytes"], "软件输入档案已变：" + name)
    for name, expected in record["fpu_baseline_rtl"].items():
        require(digest(args.baseline_core / name) == expected, "FPU 基线输入已变：" + name)
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=repo), "先提交全部公开文件，再打包")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    uart, sources = out / "uart", out / "sources"
    uart.mkdir(); sources.mkdir()
    copy(args.bitstream, uart, "toy_a7_uart.bit")
    copy(args.payload, uart, "fw_payload.bin")
    copy(args.validation, uart, "VALIDATION_RESULT.json")
    copy(evidence_path("2026-10-12/linux-gemmini/build/LINUX_GEMMINI_BUILD.json"), uart, "LINUX_GEMMINI_BUILD.json")
    for name in ["README.md", "run_uart.ps1", "verify_bundle.py"]:
        copy(ROOT / "distribution-rob" / name, uart, name)
    copy(repo / "LICENSE", uart, "LICENSE")
    copy(ROOT / "program.tcl", uart, "program.tcl")
    for path in (ROOT / "host").glob("*.py"):
        copy(path, uart, path.relative_to(ROOT))
    for path in (ROOT / "board").rglob("*"):
        if path.is_file() and (path.suffix in [".sv", ".tcl", ".xdc", ".xml", ".prj"] or "vendor" in path.parts):
            copy(path, uart, path.relative_to(ROOT))
    for name in ["ToyLinuxChip.sv", "FpgaMemories.sv", "MEMORY_MANIFEST.json"]:
        copy(args.core_dir / name, uart, "build/serial-bound/" + name)
    shutil.copytree(args.os_inputs / "notices", uart / "notices")
    (uart / "requirements.txt").write_text("pyserial==3.5\n")
    bind(uart, "ROB_PR10_UART", commit)
    tracked = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=repo).decode().split("\0")
    submodules = {}
    for entry in tracked:
        if entry:
            metadata, name = entry.split("\t", 1)
            mode, object_id, _ = metadata.split()
            if mode == "160000":
                submodules[name] = object_id
            else:
                copy(repo / name, sources, "repository/" + name)
    (sources / "SUBMODULES.json").write_text(json.dumps(submodules, indent=2) + "\n")
    copy(args.validation, sources, "VALIDATION_RESULT.json")
    shutil.copytree(args.os_inputs / "build", sources / "software-inputs/build")
    copy(args.os_inputs / "INPUTS.json", sources, "software-inputs/INPUTS.json")
    shutil.copytree(args.os_inputs / "notices", sources / "notices")
    for name in ["ToyLinuxChip.sv", "FpgaMemories.sv", "MEMORY_MANIFEST.json"]:
        copy(args.core_dir / name, sources, "generated/" + name)
    for name in record["fpu_baseline_rtl"]:
        copy(args.baseline_core / name, sources, "reference-fpu/" + name)
    bind(sources, "ROB_PR10_SOURCES", commit)
    for kind, directory in [("uart", uart), ("sources", sources)]:
        compress(directory, out / ("arty-a7-rob-pr10-" + kind + ".zip"))
    for path, name in [(args.bitstream, "toy_a7_rob_pr10_uart.bit"),
                       (ROOT / "board/program_arty.tcl", "program_arty.tcl"),
                       (ROOT / "board/build_board.tcl", "build_board.tcl")]:
        copy(path, out, name)
    assets = {path.name: {"sha256": digest(path), "bytes": path.stat().st_size} for path in sorted(out.iterdir()) if path.is_file()}
    (out / "SHA256SUMS.txt").write_text("".join(item["sha256"] + "  " + name + "\n" for name, item in assets.items()))
    (out / "RELEASE_MANIFEST.json").write_text(json.dumps({"source_commit": commit,
        "validation_input_commit": record["source_commit"], "engineering_prerelease": True,
        "physical_hardware_tested": False, "assets": assets}, indent=2) + "\n")
    print("PASS packaged ROB/PR10 prerelease:", out)


if __name__ == "__main__":
    main()
