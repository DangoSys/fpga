"""Run the existing CPU/VM/FPU oracle through the real board platform RTL.

The DDR PHY/CDC is replaced by a stalled AXI memory model here. Loader start is
forced only in this testbench so this separately tests CPU-to-DDR/SCU wiring.
"""
import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build/board-cpu"


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test",choices=("cpu","gemmini","loop","dma"),default="cpu")
    args=parser.parse_args()
    OUT=ROOT/("build/board-"+args.test)
    OUT.mkdir(parents=True,exist_ok=True)
    binary=ROOT/"build/cpu-smoke/smoke.bin"
    if args.test!="cpu":
        subdir={"gemmini":"gemmini-tests","loop":"loop-stress","dma":"dma-beat64"}[args.test]
        elf=ROOT/"build"/subdir/"simulation/smoke.elf"
        binary=OUT/"program.bin"
        subprocess.run(["riscv64-unknown-elf-objcopy","-O","binary",str(elf),str(binary)],check=True)
    assert binary.exists()
    shutil.copy2(binary,OUT/"smoke.bin")
    (OUT/"smoke.hex").write_text("\n".join(f"{b:02x}" for b in binary.read_bytes())+"\n")
    platform=ROOT/"board/toy_a7_platform.sv"
    header=platform.read_text().split(") (",1)[1].split(");",1)[0]
    signals=[]
    direction,width=None,""
    for part in header.split(","):
        m=re.fullmatch(r"\s*(?:(input|output)\s+wire\s+)?(\[[^]]+\]\s*)?(\w+)\s*",part)
        assert m,part
        if m[1]:direction,width=m[1],m[2] or ""
        signals.append((direction,width,m[3]))
    lines=["`timescale 1ns/1ps","module tb_board_cpu;", "  reg clk=0;always #5 clk=~clk;",
           "  reg reset=1,uart_rx_in=1;"]
    for _,width,name in signals:
        if name not in ("clk","reset","uart_rx_in"):lines.append(f"  wire {width}{name};")
    lines += ["  toy_a7_platform platform(.*);", "  initial begin",
              "    repeat(10) @(negedge clk); force platform.loader.cpu_run=1;reset=0;end",
              "  integer cycles=0;",
              "  always @(posedge clk) if(!reset) begin",
              "    cycles<=cycles+1;",
              "    if(platform.memory_aw_valid && platform.memory_aw_bits_lock) $fatal(1,\"Unexpected AXI exclusive write\");",
              "    if(platform.memory_ar_valid && platform.memory_ar_bits_lock) $fatal(1,\"Unexpected AXI exclusive read\");",
              "    if(ddr_awvalid && ddr_awready && (ddr_awsize!=4 || ddr_awlen!=0)) $fatal(1,\"Narrow DDR write\");",
              "    if(ddr_arvalid && ddr_arready && (ddr_arsize!=4 || ddr_arlen!=0)) $fatal(1,\"Narrow DDR read\");",
              "    if(exited && (exit_code & 32'hffff0000)==32'hbad00000) $fatal(1,\"CPU oracle failed stage=%h\",exit_code);",
              "    if(exited && exit_code==32'h600d600d) begin",
              '      $display("PASS CPU Sv39/FPU/AMO/cache/interrupt through board AXI/SCU cycles=%0d",cycles);$finish;end',
              "    if(cycles>4000000) $fatal(1,\"Board CPU watchdog\");",
              "  end"]
    mapping={"awid":"aw_bits_id","awaddr":"aw_bits_addr","awlen":"aw_bits_len","awsize":"aw_bits_size",
             "awburst":"aw_bits_burst","wdata":"w_bits_data","wstrb":"w_bits_strb","wlast":"w_bits_last",
             "bid":"b_bits_id","bresp":"b_bits_resp","arid":"ar_bits_id","araddr":"ar_bits_addr",
             "arlen":"ar_bits_len","arsize":"ar_bits_size","arburst":"ar_bits_burst","rid":"r_bits_id",
             "rdata":"r_bits_data","rresp":"r_bits_resp","rlast":"r_bits_last"}
    connections=[".clock(clk)",".reset(reset)"]
    for _,_,name in signals:
        if name.startswith("ddr_"):
            suffix=name[4:]
            connections.append(f".{mapping.get(suffix,suffix.replace('ready','_ready').replace('valid','_valid'))}({name})")
    lines += ['  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(262144),.IMAGE("smoke.hex")) memory (',
              "    "+",\n    ".join(connections)+"\n  );","endmodule"]
    bench=OUT/"tb_board_cpu.sv"
    bench.write_text("\n".join(lines)+"\n")
    files=[ROOT/"build/serial-bound/ToyLinuxChip.sv",ROOT/"build/serial-bound/FpgaMemories.sv",
           ROOT/"tests/axi_smoke_memory.sv",bench]+[p for p in (ROOT/"board").glob("*.sv") if p.name!="toy_a7_top.sv"]
    with (OUT/"compile.log").open("w") as log:
        subprocess.run(["verilator","--binary","--timing","-j","8","-Wno-fatal","-DSYNTHESIS",
                        "-DBUCKYBALL_DISABLE_DPI","--top-module","tb_board_cpu","--Mdir",str(OUT/"obj")]+[str(p) for p in files],
                       stdout=log,stderr=log,check=True,timeout=900)
    result=subprocess.run([str(OUT/"obj/Vtb_board_cpu")],cwd=OUT,capture_output=True,text=True,timeout=180)
    (OUT/"simulation.log").write_text(result.stdout+result.stderr)
    print(result.stdout)
    result.check_returncode()
    assert "PASS CPU Sv39/FPU/AMO/cache/interrupt through board AXI/SCU" in result.stdout
    record=dict(result="PASS",test=args.test,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                original_cpu_oracle=True,ddr_phy_simulated=False,physical_linux_boot_tested=False,
                cycles=int(re.search(r"cycles=(\d+)",result.stdout)[1]))
    (OUT/"RESULT.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__=="__main__":
    main()
