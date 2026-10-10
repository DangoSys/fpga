"""Bind CIRCT single-port SRAM macros to synchronous FPGA RAM templates.

The emitted CPU/operator RTL is not rewritten. Only compiler-declared external
memory modules receive implementations. Undefined read results during a write
or disabled cycle hold their previous value. No memory contents are reset.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


def unpack_emission(raw):
    parts = re.split(r'// ----- 8< ----- FILE "([^"]+)" ----- 8< -----', raw)
    rtl = [parts[0]]
    metadata = None
    config = None
    for name, body in zip(parts[1::2], parts[2::2]):
        if name.endswith((".sv", ".v")):
            rtl.append(body)
        elif name == "metadata/seq_mems.json":
            assert metadata is None
            metadata = json.loads(body)
        elif name.endswith("/memories.conf"):
            assert config is None
            config = body.strip() + "\n"
        elif name == "firrtl_black_box_resource_files.f":
            assert all(x.strip().endswith(".v") for x in body.splitlines() if x.strip())
        else:
            raise ValueError(f"Unrecognized emitted section: {name}")
    assert metadata and config, "Elaborate with --fpga-memories first"
    return "\n".join(rtl), metadata, config


def validate(metadata, config):
    entries = {}
    for line in config.splitlines():
        words = line.split()
        assert len(words) % 2 == 0
        row = dict(zip(words[::2], words[1::2]))
        assert set(row) <= {"name", "depth", "width", "ports", "mask_gran"}
        assert row["ports"] in ("rw", "mrw"), row
        assert row["name"] not in entries
        entries[row["name"]] = row
    assert len(entries) == len(metadata)
    for mem in metadata:
        name = mem["module_name"]
        assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
        assert (mem["read"], mem["write"], mem["readwrite"]) == (0, 0, 1)
        assert not mem["extra_ports"]
        row = entries[name]
        assert int(row["depth"]) == mem["depth"] > 1
        assert int(row["width"]) == mem["width"] > 0
        assert (row["ports"] == "mrw") == mem["masked"]
        if mem["masked"]:
            gran = mem["mask_granularity"]
            assert int(row["mask_gran"]) == gran and mem["width"] % gran == 0


def emit_memory(mem):
    name, depth, width = (mem[k] for k in ("module_name", "depth", "width"))
    gran = mem.get("mask_granularity", width)
    lanes = width // gran
    addr = (depth - 1).bit_length()
    # Small cache tags suit LUT RAM. Data banks/caches use physical block RAM.
    style = "distributed" if "tag_array" in name and depth <= 64 else "block"
    ports = [
        f"  input [{addr-1}:0] RW0_addr",
        "  input RW0_en, RW0_clk, RW0_wmode",
        f"  input [{width-1}:0] RW0_wdata",
        f"  output reg [{width-1}:0] RW0_rdata",
    ]
    if mem["masked"]:
        ports.append(f"  input [{lanes-1}:0] RW0_wmask")
    lines = [f"module {name}(" + ",\n".join(ports) + "\n);"]
    # Native byte masks share a wide array. Other mask widths get independent
    # arrays so e.g. 17-bit L2 tags never require unsupported byte enables.
    if not mem["masked"] or gran in (8, 9):
        lines += [
            f'  (* ram_style = "{style}" *) reg [{width-1}:0] ram [0:{depth-1}];',
            "  always @(posedge RW0_clk) begin",
            "    if (RW0_en) begin",
            "      if (RW0_wmode) begin",
        ]
        if mem["masked"]:
            lines += [
                f"        for (integer lane = 0; lane < {lanes}; lane = lane + 1)",
                "          if (RW0_wmask[lane])",
                f"            ram[RW0_addr][lane*{gran} +: {gran}] <= "
                f"RW0_wdata[lane*{gran} +: {gran}];",
            ]
        else:
            lines.append("        ram[RW0_addr] <= RW0_wdata;")
        lines += [
            "      end else RW0_rdata <= ram[RW0_addr];",
            "    end",
            "  end",
        ]
    else:
        lines += [
            f"  for (genvar lane = 0; lane < {lanes}; lane = lane + 1) begin : lanes",
            f'    (* ram_style = "{style}" *) reg [{gran-1}:0] ram [0:{depth-1}];',
            "    always @(posedge RW0_clk) begin",
            "      if (RW0_en) begin",
            "        if (RW0_wmode) begin",
            "          if (RW0_wmask[lane]) ram[RW0_addr] <= "
            f"RW0_wdata[lane*{gran} +: {gran}];",
            f"        end else RW0_rdata[lane*{gran} +: {gran}] <= ram[RW0_addr];",
            "      end",
            "    end",
            "  end",
        ]
    return "\n".join(lines + ["endmodule", ""]), style


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("emission", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw = args.emission.read_bytes()
    rtl, metadata, config = unpack_emission(raw.decode())
    validate(metadata, config)
    modules, mappings = [], []
    for mem in metadata:
        module, style = emit_memory(mem)
        modules.append(module)
        mappings.append({**mem, "ram_style": style})
    macros = "\n".join(modules)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "PebbleLinuxChip.sv").write_bytes(rtl.encode())
    (args.output_dir / "FpgaMemories.sv").write_bytes(macros.encode())
    (args.output_dir / "memories.conf").write_bytes(config.encode())
    record = {
        "emitted_sha256": hashlib.sha256(raw).hexdigest(),
        "core_rtl_sha256": hashlib.sha256(rtl.encode()).hexdigest(),
        "memory_rtl_sha256": hashlib.sha256(macros.encode()).hexdigest(),
        "read_latency": 1,
        "write_latency": 1,
        "undefined_output_policy": "hold on disabled/write cycle",
        "memories": mappings,
    }
    (args.output_dir / "MEMORY_MANIFEST.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    instances = sum(len(m["hierarchy"]) for m in metadata)
    print(f"Bound {len(metadata)} memory types, {instances} instances")


if __name__ == "__main__":
    main()
