"""打包已归档且摘要固定的两套烧录产物，不构建、不连接或写入板卡。"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "distribution"
ARCHIVE = ROOT / "evidence/2026-10-12"
TAG = "arty-a7-toy-2026-10-12"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def copy(source, root, relative):
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def bind_file(path):
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def manifest(root, flow, commit):
    files = {p.relative_to(root).as_posix(): bind_file(p)
             for p in sorted(root.rglob("*")) if p.is_file()}
    result = {"flow": flow, "source_commit": commit,
              "target": "xc7a100tcsg324-1", "engineering_prerelease": True,
              "files": files}
    (root / "MANIFEST.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def zip_directory(source, target):
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as output:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                # Upstream source .tar.gz files are already compressed.
                method = zipfile.ZIP_STORED if path.name.endswith(".tar.gz") else zipfile.ZIP_DEFLATED
                output.write(path, path.relative_to(source).as_posix(), compress_type=method)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["uart-bit", "uart-payload", "flash-bit", "flash-packed", "flash-mcs", "os-inputs", "output"]:
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"],
                                       cwd=ROOT, text=True).strip())
    require(not subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                         cwd=repo), "先提交全部公开源码，拒绝打包未提交的修改")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    build = read(ARCHIVE / "linux-gemmini/build/LINUX_GEMMINI_BUILD.json")
    uart_record = read(ARCHIVE / "hardware/PROGRAM_RESULT.json")
    flash_record = read(ARCHIVE / "flash/FLASH_RESULT.json")
    flash_image = read(ARCHIVE / "flash/software/FLASH_IMAGE.json")
    expected = [(args.uart_bit, uart_record["bitstream_sha256"]),
                (args.uart_payload, build["payload_sha256"]),
                (args.flash_bit, flash_record["bitstream_sha256"]),
                (args.flash_packed, flash_image["packed_payload_sha256"]),
                (args.flash_mcs, flash_image["flash_image_sha256"])]
    for path, sha in expected:
        require(digest(path) == sha, "烧录文件与已归档实物证据不符：" + path.name)
    require(args.uart_payload.stat().st_size == build["payload_bytes"], "软件镜像长度错误")
    baseline = read(ROOT / "SOFTWARE_BASELINE.json")
    cache_log = (ARCHIVE / "linux-gemmini/build/build.log").read_text(encoding="utf-8")
    cache_hashes = dict(re.findall(r"^CACHE (\S+) ([0-9a-f]{64})$", cache_log, re.MULTILINE))
    os_files = []
    for name, version in baseline.items():
        path = args.os_inputs / "build/downloads" / f"{name}-{version}.tar.gz"
        require(digest(path) == cache_hashes[name], "依赖归档摘要不符：" + name)
        os_files.append(path)
    input_record = read(args.os_inputs / "INPUTS.json")
    for name in ["build/software/kernel-build/linux/.config",
                 "build/software/kernel-build/busybox/.config",
                 "build/software/SOURCE_MANIFEST.json"]:
        require(bind_file(args.os_inputs / name) == input_record[name], "实际软件配置摘要不符")
    notices = args.os_inputs / "notices"
    require((notices / "thirdparty/rocket-chip/LICENSE.Berkeley").is_file(), "缺少硬件依赖声明")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    package_roots = {name: output / name for name in ["uart", "flash", "sources"]}
    for name in ["uart", "flash"]:
        root = package_roots[name]
        root.mkdir()
        copy(TEMPLATES / "verify_bundle.py", root, "verify_bundle.py")
        copy(TEMPLATES / f"{name.upper()}_README.md", root, "README.md")
        copy(TEMPLATES / f"run_{name}.ps1", root, f"run_{name}.ps1")
        copy(repo / "LICENSE", root, "LICENSE")
        shutil.copytree(notices, root / "notices")
        (root / "requirements.txt").write_text("pyserial==3.5\n", encoding="utf-8")

    uart = package_roots["uart"]
    copy(args.uart_bit, uart, "toy_a7_uart.bit")
    copy(args.uart_payload, uart, "fw_payload.bin")
    copy(ARCHIVE / "linux-gemmini/build/LINUX_GEMMINI_BUILD.json", uart, "LINUX_GEMMINI_BUILD.json")
    for name in ["program.tcl", "board/program_arty.tcl", "host/check_linux_gemmini.py",
                 "host/ftdi_transport.py", "host/load.py", "scripts/verify_linux_gemmini.py"]:
        copy(ROOT / name, uart, name)
    shutil.copytree(ARCHIVE / "linux-gemmini", uart / "evidence/linux-gemmini")
    copy(ARCHIVE / "hardware/PROGRAM_RESULT.json", uart, "evidence/PROGRAM_RESULT.json")

    flash = package_roots["flash"]
    copy(args.flash_bit, flash, "toy_a7_flash.bit")
    copy(args.flash_packed, flash, "flash_payload.bin")
    copy(args.flash_mcs, flash, "toy_flash.mcs")
    copy(ARCHIVE / "flash/software/FLASH_IMAGE.json", flash, "toy_flash.mcs.json")
    for name in ["host/flash.py", "host/observe_flash_boot.py", "board/program_flash.tcl",
                 "board/make_flash_image.tcl"]:
        copy(ROOT / name, flash, name)
    shutil.copytree(ARCHIVE / "flash", flash / "evidence/flash")

    sources = package_roots["sources"]
    sources.mkdir()
    snapshot = subprocess.check_output(["git", "archive", "--format=zip", "--prefix=fpga/", commit], cwd=repo)
    with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
        archive.extractall(sources)
    copy(TEMPLATES / "SOURCES_README.md", sources, "README.md")
    copy(TEMPLATES / "verify_bundle.py", sources, "verify_bundle.py")
    (sources / "SOURCE_COMMIT.txt").write_text(commit + "\n", encoding="utf-8")
    shutil.copytree(notices, sources / "notices")
    for path in os_files:
        copy(path, sources, "fpga/platforms/arty-a7-toy/build/downloads/" + path.name)
    for name, target in [("linux/.config", "linux.config"), ("busybox/.config", "busybox.config")]:
        copy(args.os_inputs / "build/software/kernel-build" / name, sources, "actual-configs/" + target)
    copy(args.os_inputs / "build/software/SOURCE_MANIFEST.json", sources, "actual-configs/SOURCE_MANIFEST.json")

    bundles = {}
    for flow, root in package_roots.items():
        metadata = manifest(root, flow, commit)
        filename = f"arty-a7-toy-{flow}.zip"
        zip_directory(root, output / filename)
        bundles[filename] = {**bind_file(output / filename), "files": len(metadata["files"])}
        print(f"PACKED {filename} files={len(metadata['files'])}", flush=True)
    # Also make the two .bit files directly downloadable, with explicit flow names.
    for name, source in [("toy_a7_uart.bit", args.uart_bit), ("toy_a7_flash.bit", args.flash_bit)]:
        copy(source, output, name)
        bundles[name] = bind_file(output / name)
    record = {"tag": TAG, "source_commit": commit, "engineering_prerelease": True,
              "assets": bundles}
    (output / "RELEASE_MANIFEST.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bundles["RELEASE_MANIFEST.json"] = bind_file(output / "RELEASE_MANIFEST.json")
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{metadata['sha256']}  {name}\n" for name, metadata in bundles.items()), encoding="utf-8")
    print("PASS DOWNLOAD_PACKAGING " + commit, flush=True)


if __name__ == "__main__":
    main()
