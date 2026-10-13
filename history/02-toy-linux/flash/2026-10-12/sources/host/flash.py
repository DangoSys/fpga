"""Back up/program/verify Flash and check automatic Linux startup, within 1 hour."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import time

from observe_flash_boot import Observer

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vivado", default="vivado")
    p.add_argument("--bitstream", type=Path, required=True)
    p.add_argument(
        "--payload",
        type=Path,
        required=True,
        help="Packed TOYFLZ4 software, not the raw image",
    )
    p.add_argument("--part", required=True)
    p.add_argument(
        "--mcs",
        type=Path,
        help="Existing Vivado-packed image if the programming host lacks Artix build support",
    )
    p.add_argument("--port", required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    bit = args.bitstream.resolve()
    payload = args.payload.resolve()
    out = args.out or ROOT / "build" / (
        "flash-program-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    image = out / "toy_flash.mcs"
    backup = out / "flash-before.bin"
    commands = [
        [
            args.vivado,
            "-mode",
            "batch",
            "-source",
            str(ROOT / "board/make_flash_image.tcl"),
            "-log",
            str(out / "image.log"),
            "-journal",
            str(out / "image.jou"),
            "-tclargs",
            str(bit),
            str(payload),
            str(image),
        ],
        [
            args.vivado,
            "-mode",
            "batch",
            "-source",
            str(ROOT / "board/program_flash.tcl"),
            "-log",
            str(out / "program.log"),
            "-journal",
            str(out / "program.jou"),
            "-tclargs",
            str(image),
            args.part,
            str(backup),
        ],
    ]
    if args.mcs:
        packed_record = json.loads(
            args.mcs.with_suffix(args.mcs.suffix + ".json").read_text()
        )
        assert packed_record["result"] == "PASS_VIVADO_FLASH_PACK"
        assert packed_record["bitstream_sha256"] == sha(bit)
        assert packed_record["packed_payload_sha256"] == sha(payload)
        assert packed_record["flash_image_sha256"] == sha(args.mcs)
        shutil.copy2(args.mcs.resolve(), image)
        commands[0] = None
    record = dict(
        status="RUNNING",
        timeout_seconds=3600,
        bitstream_sha256=sha(bit),
        packed_payload_sha256=sha(payload),
        part=args.part,
        port=args.port,
        started_at=datetime.now().astimezone().isoformat(),
        commands=commands,
    )
    result = out / "RESULT.json"
    result.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    watcher = None
    try:
        for i, command in enumerate(commands):
            if command is None:
                print("USING_PREPACKED_FLASH_IMAGE", sha(image), flush=True)
                continue
            if i == 1:
                watcher = Observer(args.port, out / "linux-console.log", timeout=3600)
                watcher.start()
            with (out / f"command-{i}.log").open("w") as log:
                proc = subprocess.Popen(
                    command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT
                )
                try:
                    code = proc.wait(
                        timeout=max(1, 3600 - (time.monotonic() - started))
                    )
                except subprocess.TimeoutExpired:
                    if __import__("os").name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                            capture_output=True,
                        )
                    else:
                        proc.kill()
                    proc.wait()
                    raise
                if code:
                    raise RuntimeError(
                        f"Vivado command {i} failed with {code}; inspect {out}"
                    )
            print("PASS FLASH_STAGE", i, flush=True)
        # Program completion may precede CPU decompression; cap the remaining wait.
        watcher.thread.join(timeout=max(1, 3600 - (time.monotonic() - started)))
        if watcher.thread.is_alive():
            raise TimeoutError("One-hour Flash/Linux timeout")
        hardware = watcher.finish()
        record.update(
            status="PASS",
            hardware=hardware,
            backup_sha256=sha(backup),
            backup_bytes=backup.stat().st_size,
            flash_image_sha256=sha(image),
        )
    except Exception as error:
        record.update(status="FAILED", error=str(error))
        raise
    finally:
        if watcher is not None:
            watcher.stop.set()
            watcher.thread.join(timeout=6)
        record.update(
            elapsed_seconds=round(time.monotonic() - started, 3),
            finished_at=datetime.now().astimezone().isoformat(),
        )
        result.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
