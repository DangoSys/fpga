"""Use Vivado to pack Flash, then record hashes for a separate programming host."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vivado", default="vivado")
    p.add_argument("--bitstream", required=True, type=Path)
    p.add_argument("--payload", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    bit, payload, out = (
        args.bitstream.resolve(),
        args.payload.resolve(),
        args.out.resolve(),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    command = [
        args.vivado,
        "-mode",
        "batch",
        "-source",
        str(ROOT / "board/make_flash_image.tcl"),
        "-log",
        str(out.with_suffix(".log")),
        "-journal",
        str(out.with_suffix(".jou")),
        "-tclargs",
        str(bit),
        str(payload),
        str(out),
    ]
    with out.with_suffix(".console.log").open("w") as log:
        subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=180,
        )
    record = dict(
        result="PASS_VIVADO_FLASH_PACK",
        bitstream_sha256=sha(bit),
        packed_payload_sha256=sha(payload),
        flash_image_sha256=sha(out),
        configuration_offset=0,
        software_offset=0x400000,
        flash_bytes=0x1000000,
    )
    out.with_suffix(out.suffix + ".json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
