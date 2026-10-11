"""Real CPU executes ROM -> serial Flash -> decompression -> original oracle.

DDR starts empty; no forced RUN or CPU reset bypass. SPI Flash and DDR PHY are
simulation models. Two corrupted images must halt in ROM without launching.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/flash-regression"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--image", type=Path, required=True, help="Packed original CPU smoke image"
    )
    p.add_argument("--skip-build", action="store_true")
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    image = args.image.read_bytes()
    (OUT / "flash.hex").write_text("\n".join(f"{b:02x}" for b in image) + "\n")
    text = (ROOT / "board/toy_a7_platform.sv").read_text()
    header = text.split(") (", 1)[1].split(");", 1)[0]
    signals = []
    direction, width = None, ""
    for part in header.split(","):
        m = re.fullmatch(
            r"\s*(?:(input|output)\s+wire\s+)?(\[[^]]+\]\s*)?(\w+)\s*", part
        )
        assert m, part
        if m[1]:
            direction, width = m[1], m[2] or ""
        signals.append((direction, width, m[3]))
    lines = [
        "`timescale 1ns/1ps",
        "module tb_flash_boot;",
        "  reg clk=0;always #20 clk=~clk;",
        "  reg reset=1;",
        "  wire uart_rx_in=1,flash_recovery=0;",
    ]
    for _, width, name in signals:
        if name not in ("clk", "reset", "uart_rx_in", "flash_recovery"):
            lines.append(f"  wire {width}{name};")
    lines += [
        "  toy_a7_platform #(.FLASH_BOOT(1)) platform(.*);",
        "  initial begin repeat(10) @(negedge clk);reset=0;end",
        f'  spi_flash_model #(.BYTES({len(image)}),.IMAGE("{OUT}/flash.hex")) flash',
        "    (.sck(flash_sck),.cs_n(flash_cs_n),.mosi(flash_mosi),.miso(flash_miso));",
        "  integer cycles=0;reg [255:0] tail=0;reg verified=0;",
        "  always @(posedge clk) if(!reset) begin",
        "    cycles<=cycles+1;",
        "    if(platform.mmio_tx_valid && platform.tx_ready) begin",
        '      $write("%c",platform.mmio_tx_data);$fflush();',
        "      tail={tail[247:0],platform.mmio_tx_data};",
        '      if(tail[175:0]=="PASS FLASH_PAYLOAD_CRC") verified=1;',
        "    end",
        "    if(exited && exit_code==32'h600d600d) begin",
        '      if(!verified) $fatal(1,"Oracle ran before verified Flash payload");',
        '      if($test$plusargs("bad_header") || $test$plusargs("bad_payload")) $fatal(1,"Corrupted image launched");',
        '      $display("PASS FLASH_CPU_ORACLE cycles=%0d",cycles);$finish;end',
        "    if(exited && exit_code==32'hbad0f101) begin",
        '      if(!$test$plusargs("bad_header") && !$test$plusargs("bad_payload")) $fatal(1,"Valid image rejected");',
        '      if(verified) $fatal(1,"Corrupt image reported verified");',
        '      $display("PASS FLASH_CORRUPTION_REJECTED cycles=%0d",cycles);$finish;end',
        "    if(exited && (exit_code & 32'hffff0000)==32'hbad00000 && exit_code!=32'hbad0f101)",
        '      $fatal(1,"CPU/ROM trap %h",exit_code);',
        '    if(cycles>40000000) $fatal(1,"Flash boot watchdog");',
        "  end",
    ]
    mapping = {
        "awid": "aw_bits_id",
        "awaddr": "aw_bits_addr",
        "awlen": "aw_bits_len",
        "awsize": "aw_bits_size",
        "awburst": "aw_bits_burst",
        "wdata": "w_bits_data",
        "wstrb": "w_bits_strb",
        "wlast": "w_bits_last",
        "bid": "b_bits_id",
        "bresp": "b_bits_resp",
        "arid": "ar_bits_id",
        "araddr": "ar_bits_addr",
        "arlen": "ar_bits_len",
        "arsize": "ar_bits_size",
        "arburst": "ar_bits_burst",
        "rid": "r_bits_id",
        "rdata": "r_bits_data",
        "rresp": "r_bits_resp",
        "rlast": "r_bits_last",
    }
    connections = [".clock(clk)", ".reset(reset)"]
    for _, _, name in signals:
        if name.startswith("ddr_"):
            s = name[4:]
            connections.append(
                f".{mapping.get(s,s.replace('ready','_ready').replace('valid','_valid'))}({name})"
            )
    lines += [
        "  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(268435456)) memory (",
        "    " + ",\n    ".join(connections) + "\n  );",
        "endmodule",
    ]
    bench = OUT / "tb_flash_boot.sv"
    bench.write_text("\n".join(lines) + "\n")
    if not args.skip_build:
        files = [
            ROOT / "build/flash-boot/ToyLinuxChip.sv",
            ROOT / "build/serial-bound/FpgaMemories.sv",
            ROOT / "tests/axi_smoke_memory.sv",
            ROOT / "tests/spi_flash_model.sv",
            bench,
        ]
        files += [f for f in (ROOT / "board").glob("*.sv") if f.name != "toy_a7_top.sv"]
        with (OUT / "compile.log").open("w") as log:
            subprocess.run(
                [
                    "verilator",
                    "--binary",
                    "--timing",
                    "-j",
                    "8",
                    "-Wno-fatal",
                    "-DSYNTHESIS",
                    "-DBUCKYBALL_DISABLE_DPI",
                    "--top-module",
                    "tb_flash_boot",
                    "--Mdir",
                    str(OUT / "obj"),
                ]
                + [str(f) for f in files],
                stdout=log,
                stderr=log,
                check=True,
                timeout=900,
                cwd=ROOT,
            )
    results = {}
    for case in ("valid", "bad_header", "bad_payload"):
        command = [str(OUT / "obj/Vtb_flash_boot")]
        if case != "valid":
            command.append("+" + case)
        with (OUT / (case + ".log")).open("w") as log:
            subprocess.run(
                command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=300,
            )
        output = (OUT / (case + ".log")).read_text()
        print(output)
        marker = (
            "PASS FLASH_CPU_ORACLE"
            if case == "valid"
            else "PASS FLASH_CORRUPTION_REJECTED"
        )
        assert marker in output
        results[case] = int(re.search(r"cycles=(\d+)", output)[1])
    (OUT / "RESULT.json").write_text(
        json.dumps(
            dict(
                result="PASS",
                cycles=results,
                empty_ddr=True,
                original_cpu_oracle=True,
                forced_run=False,
                physical_flash_tested=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
