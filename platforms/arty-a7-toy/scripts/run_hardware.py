"""从仓库准备固定 UART 发布包，复用原实板验证器；--prepare-only 不访问硬件。"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import subprocess
import sys
import time
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def require(value, message):
    if not value:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def check_archive(path, release):
    require(path.stat().st_size == release["archive_bytes"] and
            digest(path) == release["archive_sha256"], "UART 包与固定发布摘要不匹配：" + str(path))


def unpack(archive, destination):
    # Validate all names before writing anything, including Windows aliases/ADS.
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        names = set()
        total = 0
        for item in package.infolist():
            name = item.filename
            parts = PurePosixPath(name).parts
            require(parts and not name.startswith("/") and "\\" not in name and
                    all(part not in [".", ".."] and ":" not in part and
                        not part.endswith((".", " ")) for part in parts), "ZIP 路径无效：" + name)
            require(stat.S_IFMT(item.external_attr >> 16) != stat.S_IFLNK, "ZIP 不允许符号链接")
            require(name.casefold() not in names, "ZIP 文件名重复：" + name)
            names.add(name.casefold())
            require((destination / name).resolve().is_relative_to(destination), "ZIP 路径越界")
            total += item.file_size
        require(total <= 256 * 1024 * 1024, "UART 包解压大小异常")
        package.extractall(destination)


def check_bundle(directory, release):
    require(digest(directory / "MANIFEST.json") == release["manifest_sha256"], "缓存清单与固定发布不匹配")
    spec = importlib.util.spec_from_file_location("hardware_bundle_verifier", ROOT / "distribution-rob/verify_bundle.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    manifest = verifier.verify(directory)
    for field in ["flow", "target", "source_commit"]:
        require(manifest[field] == release[field], "发布包配置不匹配：" + field)
    validation = read_json(directory / "VALIDATION_RESULT.json")
    require(validation["result"] == "PASS_ROB_PR10_FULL_VALIDATION" and
            validation["source_commit"] == release["validation_input_commit"] and
            validation["profile"] == release["profile"], "发布包缺少对应实现/RTL 验证")
    for name, field in [("toy_a7_uart.bit", "bitstream_sha256"), ("fw_payload.bin", "payload_sha256")]:
        require(manifest["files"][name]["sha256"] == validation[field] == release[field], "位流/软件版本不匹配")
    software = read_json(directory / "LINUX_GEMMINI_BUILD.json")
    require(software["payload_sha256"] == release["payload_sha256"] and
            software["payload_bytes"] == release["payload_bytes"] and
            len(software["workloads"]) == release["test_count"], "软件测试清单不匹配")
    return directory


def prepare(release, cache, supplied_archive=None):
    cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "uart.zip"
    if supplied_archive:
        supplied_archive = supplied_archive.resolve()
        check_archive(supplied_archive, release)
    if archive.exists():
        check_archive(archive, release)
    else:
        partial = cache / ("uart-" + uuid.uuid4().hex + ".part")
        try:
            if supplied_archive:
                shutil.copyfile(supplied_archive, partial)
            else:
                print("下载固定 UART 发布包：" + release["tag"], flush=True)
                request = urllib.request.Request(release["url"], headers={"User-Agent": "DangoSys-FPGA-hardware-check"})
                with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as stream:
                    received = 0
                    started = time.monotonic()
                    while block := response.read(1024 * 1024):
                        received += len(block)
                        require(received <= release["archive_bytes"], "下载文件超过固定大小")
                        if time.monotonic() - started > 300:
                            raise TimeoutError("下载超过 300 秒；可用 --bundle-zip 指定本地发布包")
                        stream.write(block)
            check_archive(partial, release)
            partial.rename(archive)
        finally:
            if partial.exists():
                partial.unlink()
    bundle = cache / "bundle"
    if not bundle.exists():
        staging = cache / ("staging-" + uuid.uuid4().hex)
        staging.mkdir()
        unpack(archive, staging)
        check_bundle(staging, release)
        require(staging.resolve().is_relative_to(cache) and bundle.resolve().is_relative_to(cache), "缓存路径越界")
        staging.rename(bundle)
    return check_bundle(bundle, release)


def check_host(port, vivado):
    require(os.name == "nt" and struct.calcsize("P") == 8, "实板入口需要 Windows 与 64 位 Python 3.10+；其他环境可使用 --prepare-only")
    require(vivado.is_file(), "未找到 Vivado：" + str(vivado))
    require(Path("C:/Windows/System32/ftd2xx.dll").is_file(), "未找到 64 位 FTDI D2XX 驱动，请先安装板卡驱动")
    try:
        import serial.tools.list_ports
    except ImportError as error:
        raise RuntimeError("请先运行 python -m pip install -r host/requirements-hardware.txt") from error
    matches = [item for item in serial.tools.list_ports.comports() if item.device.casefold() == port.casefold()]
    require(len(matches) == 1, "没有找到指定串口 " + port + "；请连接 PROG/UART USB 并检查设备管理器")
    device = matches[0]
    require((device.vid, device.pid) == (0x0403, 0x6010) and
            (device.serial_number or "").endswith("B"), "指定端口不是 FT2232 UART B；请勿选择 JTAG A")
    return device.device


def verify_hardware(bundle, release, port, vivado):
    before = set((bundle / "build").glob("hardware-gemmini-*/RESULT.json"))
    command = [sys.executable, "-X", "utf8", "-u", str(bundle / "host/check_linux_gemmini.py"),
               "--payload", str(bundle / "fw_payload.bin"), "--build-result", str(bundle / "LINUX_GEMMINI_BUILD.json"),
               "--bitstream", str(bundle / "toy_a7_uart.bit"), "--expected-bit-sha256", release["bitstream_sha256"],
               "--port", port, "--vivado", str(vivado)]
    print("开始临时 JTAG 配置、DDR 完整读回与 Linux/Gemmini 验证，硬超时 3600 秒。", flush=True)
    process = subprocess.Popen(command, cwd=bundle)
    try:
        code = process.wait(timeout=release["timeout_seconds"])
    except BaseException:
        # Terminate only this launched process tree, including its Vivado child.
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], timeout=15, check=False)
            process.wait(timeout=15)
        raise
    require(code == 0, "原实板验证器失败，退出码 " + str(code) + "；日志位于 " + str(bundle / "build"))
    created = set((bundle / "build").glob("hardware-gemmini-*/RESULT.json")) - before
    require(len(created) == 1, "没有取得本轮唯一实板结果，不能沿用旧 PASS")
    result_path = created.pop()
    result = read_json(result_path)
    require(result["result"] == "PASS_LINUX_AND_GEMMINI_HARDWARE" and not result["flash_written"] and
            result["bitstream_sha256"] == release["bitstream_sha256"] and
            result["payload_sha256"] == release["payload_sha256"] and
            result["ddr_readback_bytes"] == release["payload_bytes"] and
            result["test_count"] == len(result["tests"]) == release["test_count"] and
            all(item["exit_code"] == 0 for item in result["tests"]), "本轮实板结果不完整或版本不匹配")
    return result_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Windows 的 FT2232 UART B 串口，例如 COM5")
    parser.add_argument("--vivado", type=Path, help="vivado.bat 的完整路径")
    parser.add_argument("--bundle-zip", type=Path, help="已下载的固定 UART ZIP；省略则自动下载")
    parser.add_argument("--prepare-only", action="store_true", help="只下载/校验/解压，不连接串口或调用 Vivado")
    args = parser.parse_args()
    if not args.prepare_only and (not args.port or not args.vivado):
        parser.error("实板验证需要 --port 和 --vivado；离线准备请使用 --prepare-only")
    release = read_json(ROOT / "HARDWARE_RELEASE.json")
    require(release["tag"] and all(c.isalnum() or c in "-_" for c in release["tag"]), "发布标签无效")
    output = ROOT / "build/hardware-entry" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "RUNNING", "release": release, "physical_hardware_tested": False, "flash_written": False}
    started = time.monotonic()
    try:
        port = check_host(args.port, args.vivado.resolve()) if not args.prepare_only else None
        bundle = prepare(release, ROOT / "build/hardware-release" / release["tag"], args.bundle_zip)
        result["bundle_directory"] = str(bundle)
        if args.prepare_only:
            result["status"] = "PREPARED_NOT_HARDWARE_TESTED"
            print("产物准备完成；未访问硬件：" + str(bundle), flush=True)
        else:
            hardware_result = verify_hardware(bundle, release, port, args.vivado.resolve())
            result.update(status="PASS_LINUX_AND_GEMMINI_HARDWARE", physical_hardware_tested=True,
                          hardware_result=str(hardware_result))
            print("PASS 本轮实板验证；原始日志：" + str(hardware_result.parent), flush=True)
    except BaseException as error:
        result.update(status="FAILED", error=str(error))
        raise
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "RUN.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("入口记录：" + str(output / "RUN.json"), flush=True)


if __name__ == "__main__":
    main()
