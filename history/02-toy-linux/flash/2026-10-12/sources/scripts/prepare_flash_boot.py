"""Pack an unchanged payload as LZ4 and bind only the boot-ROM module.

The 4 MiB configuration partition and 12 MiB software partition cannot overlap.
Dependencies: lz4==4.4.5. Compile boot/flash_boot.c and flash_start.S separately.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = "4c6aacf64660bbbf14b1114e8d5e4439d6a4e1427aaf1f681c6a4f618f2d2779"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--payload", type=Path, required=True)
    p.add_argument("--boot-bin", type=Path, required=True)
    p.add_argument(
        "--core", type=Path, default=ROOT / "build/serial-bound/ToyLinuxChip.sv"
    )
    p.add_argument("--out", type=Path, default=ROOT / "build/flash-boot")
    args = p.parse_args()
    import lz4
    import lz4.block

    raw = args.payload.read_bytes()
    if not 0 < len(raw) <= 0x0F000000:
        raise ValueError("Payload overlaps the boot stack reservation")
    packed = lz4.block.compress(
        raw, mode="high_compression", compression=12, store_size=False
    )
    assert lz4.block.decompress(packed, uncompressed_size=len(raw)) == raw
    head = struct.pack(
        "<8s5I", b"TOYFLZ4\0", 1, len(packed), len(raw), zlib.crc32(raw), 0
    )
    image = head + struct.pack("<I", zlib.crc32(head)) + packed
    if len(image) > 0xC00000:
        raise ValueError("Compressed software exceeds the 12 MiB partition")
    original_bytes = args.core.read_bytes()
    assert (
        sha(original_bytes) == CORE_SHA
    ), "Unexpected core: use the pinned validated generation"
    original = original_bytes.decode()
    matches = list(re.finditer(r"^module TLROM\(.*?^endmodule", original, re.M | re.S))
    assert len(matches) == 1
    m = matches[0]
    original_rom = m.group()
    words = re.findall(r"64'h([0-9A-Fa-f]+)", original_rom.split("TLMonitor")[0])
    rom_bytes = b"".join(int(w, 16).to_bytes(8, "little") for w in words[::-1])
    dtb_start = rom_bytes.index(bytes.fromhex("d00dfeed"))
    dtb_size = int.from_bytes(rom_bytes[dtb_start + 4 : dtb_start + 8], "big")
    dtb = rom_bytes[dtb_start : dtb_start + dtb_size]
    assert len(dtb) == dtb_size and dtb_size <= 4096
    boot = args.boot_bin.read_bytes()
    assert 0 < len(boot) <= 4096
    rom = boot.ljust(4096, b"\0") + dtb.ljust(4096, b"\0")
    replacement = original_rom.split(");", 1)[0] + """
);
  (* rom_style="block" *) reg [63:0] contents [0:1023];
  initial $readmemh("build/flash-boot/bootrom.hex", contents);
  reg valid;
  reg [1:0] response_size;
  reg [6:0] response_source;
  reg [63:0] response_data;
  assign auto_in_a_ready=!valid || auto_in_d_ready;
  assign auto_in_d_valid=valid;
  assign auto_in_d_bits_size=response_size;
  assign auto_in_d_bits_source=response_source;
  assign auto_in_d_bits_data=response_data;
  always @(posedge clock) begin
    if(reset) valid<=0;
    else if(auto_in_a_ready) valid<=auto_in_a_valid;
    if(auto_in_a_ready && auto_in_a_valid) begin
      response_size<=auto_in_a_bits_size;response_source<=auto_in_a_bits_source;
      response_data<=|auto_in_a_bits_address[15:13] ? 64'd0 : contents[auto_in_a_bits_address[12:3]];
    end
  end
endmodule"""
    adapted = original[: m.start()] + replacement + original[m.end() :]
    assert adapted.replace(replacement, original_rom, 1) == original
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "flash_payload.bin").write_bytes(image)
    (args.out / "bootrom.hex").write_text(
        "\n".join(
            f"{int.from_bytes(rom[i:i+8], 'little'):016x}"
            for i in range(0, len(rom), 8)
        )
        + "\n"
    )
    (args.out / "ToyLinuxChip.sv").write_text(adapted, encoding="utf-8", newline="\n")
    record = dict(
        payload_bytes=len(raw),
        payload_sha256=sha(raw),
        lz4_bytes=len(packed),
        flash_image_bytes=len(image),
        flash_offset=0x400000,
        flash_bytes=0x1000000,
        lz4_version=lz4.__version__,
        boot_code_bytes=len(boot),
        boot_sha256=sha(boot),
        original_core_sha256=sha(original_bytes),
        adapted_core_sha256=sha(adapted.encode()),
        only_module_replaced="TLROM",
        dtb_sha256=sha(dtb),
        dtb_address="0x11000",
        rom_bytes=len(rom),
        payload_crc32=f"{zlib.crc32(raw):08x}",
    )
    (args.out / "MANIFEST.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
