"""从私有 SSH 配置连接，在新目录构建并下载镜像；不保存或输出凭据。"""

import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import time
import uuid

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-helper", type=Path, required=True)
    parser.add_argument("--cache-base", default="/home/yys/codex-builds/pebble-linux-20261010")
    parser.add_argument("--sdk", default="/nix/store/l4dz443kk1rr8m3z0hby213xc2wqpjyc-riscv64-linux-gnu-toolchain")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("private_ssh", args.ssh_helper)
    private = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(private)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not callable(getattr(private, "connect", None)):
        raise ValueError("Private SSH module must provide connect(client)")
    private.connect(client)
    client.get_transport().set_keepalive(30)
    started = time.monotonic()
    label = "linux-gemmini-20261012-" + uuid.uuid4().hex[:8]
    out = ROOT / "build" / label
    out.mkdir(parents=True, exist_ok=False)
    try:
        sftp = client.open_sftp()
        remote = sftp.normalize(".") + "/codex-builds/" + label
        sftp.mkdir(remote)
        files = [ROOT / "SOFTWARE_BASELINE.json", ROOT / "tests/REFERENCE_MANIFEST.json",
                 ROOT / "evidence/2026-10-11/ToyLinuxChip.profile.json",
                 ROOT / "scripts/build_board_firmware.py"]
        files += list((ROOT / "software").glob("*.py"))
        files += [ROOT / "software/build.sh", ROOT / "software/linux_system_check.c",
                  ROOT / "software/gemmini_linux_check.c"]
        files += [path for path in (ROOT / "tests/reference").rglob("*") if path.is_file()]
        directories = set()
        for path in files:
            relative = path.relative_to(ROOT)
            for parent in relative.parents:
                if str(parent) != ".":
                    directories.add(parent.as_posix())
        for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
            sftp.mkdir(remote + "/" + directory)
        for path in files:
            sftp.put(str(path), remote + "/" + path.relative_to(ROOT).as_posix())
        command = "cd " + shlex.quote(remote) + " && timeout --signal=TERM --kill-after=10s 3600s python3 -u software/build_gemmini_image.py --cache-base " + shlex.quote(args.cache_base) + " --sdk " + shlex.quote(args.sdk)
        print("REMOTE " + remote, flush=True)
        _, stdout, _ = client.exec_command(command, timeout=15)
        channel = stdout.channel
        channel.set_combine_stderr(True)
        with (out / "build.log").open("wb") as log:
            while not channel.exit_status_ready() or channel.recv_ready():
                if time.monotonic() - started > 3650:
                    channel.close()
                    raise TimeoutError("One-hour software build timeout")
                if channel.recv_ready():
                    data = channel.recv(65536)
                    log.write(data)
                    log.flush()
                    print(data.decode(errors="replace"), end="", flush=True)
                else:
                    time.sleep(0.1)
        code = channel.recv_exit_status()
        (out / "SESSION.json").write_text(json.dumps({"remote": remote, "exit_code": code,
            "timeout_seconds": 3600, "elapsed_seconds": round(time.monotonic() - started, 3)}, indent=2) + "\n")
        if code:
            raise RuntimeError(f"Remote build failed with exit {code}; see {out / 'build.log'}")
        for filename in ["build/LINUX_GEMMINI_BUILD.json", "build/board-software/fw_payload.bin",
                         "build/board-software/RESULT.json"]:
            destination = out / Path(filename).name
            sftp.get(remote + "/" + filename, str(destination))
        sftp.close()
        print("DOWNLOADED " + str(out), flush=True)
    finally:
        client.close()


if __name__ == "__main__":
    main()
