"""Compare FPGA SRAM macros with the actual pre-mapping Chisel memory RTL.

Initialize every row, exercise every write-mask lane, disabled writes, random
transactions, and read back the full memory. Check only defined read cycles.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


def find_reference(original, mem):
    for match in re.finditer(r"^module (\w+)\(.*?^endmodule", original, re.M | re.S):
        body = match.group()
        width, depth = mem["width"], mem["depth"]
        pattern = rf"reg\s+\[{width-1}:0\]\s+Memory\[0:{depth-1}\]"
        data_port = "R0_data" if mem["read"] else "RW0_wmode"
        mask_name = "W0_mask" if mem["read"] else "RW0_wmask"
        if not re.search(pattern, body) or data_port not in body:
            continue
        if mem["masked"]:
            lanes = width // mem["mask_granularity"]
            if not re.search(rf"input\s+\[{lanes-1}:0\]\s+{mask_name}", body):
                continue
        elif mask_name in body:
            continue
        name = mem["module_name"] + "_reference"
        return re.sub(r"^module \w+", "module " + name, body), name
    raise ValueError(f"No original Chisel memory matches {mem['module_name']}")


def dual_bench(mem, reference):
    name, width, depth = mem["module_name"], mem["width"], mem["depth"]
    gran = mem.get("mask_granularity", width)
    lanes = width // gran
    mask_port = ", .W0_mask(mask)" if mem["masked"] else ""
    connections = (
        ".R0_addr(ra), .R0_clk(clk), .R0_en(re), "
        ".W0_addr(wa), .W0_clk(clk), .W0_en(we), .W0_data(data)"
    )
    return f"""
module test_{name}(output reg done = 0);
  localparam W={width}, D={depth}, G={gran}, M={lanes};
  reg clk=0;
  always #5 clk=~clk;
  reg [{(depth-1).bit_length()-1}:0] ra=0, wa=0;
  reg re=0, we=0;
  reg [W-1:0] data=0;
  reg [M-1:0] mask=0;
  wire [W-1:0] actual, reference;
  reg [W-1:0] model[0:D-1];
  integer seed=98765;
  {name} dut({connections}{mask_port}, .R0_data(actual));
  {reference} original({connections}{mask_port}, .R0_data(reference));
  task step(input integer r, input integer w, input bit ren,
            input bit wen, input [M-1:0] m);
    reg [W-1:0] expected;
    begin
      @(negedge clk);
      ra=r; wa=w; re=ren; we=wen; mask=m;
      for (integer b=0; b<W; b=b+1) data[b]=$random(seed)&1;
      expected=model[r];
      @(posedge clk);
      #1;
      // CIRCT leaves simultaneous read/write of the same address undefined.
      if (ren && !(wen && r==w)) begin
        if (actual !== expected || reference !== expected)
          $fatal(1, "{name}: 1R1W mismatch r=%0d w=%0d", r, w);
        ra=(r+1)%D;
        #1;
        if (actual !== expected || reference !== expected)
          $fatal(1, "{name}: read output changed between clock edges");
      end
      if (wen) for (integer lane=0; lane<M; lane=lane+1)
        if ({'mask[lane]' if mem['masked'] else "1'b1"})
          model[w][lane*G +: G]=data[lane*G +: G];
    end
  endtask
  initial begin
    for (integer i=0; i<D; i=i+1) step(0,i,0,1,'1);
    for (integer lane=0; lane<M; lane=lane+1) begin
      step(0,lane%D,0,1,{{{{(M-1){{1'b0}}}},1'b1}} << lane);
      step(lane%D,0,1,0,'0);
    end
    for (integer i=0; i<1000; i=i+1)
      step($urandom%D,$urandom%D,$urandom%2,$urandom%2,$urandom);
    for (integer i=0; i<D; i=i+1) step(i,(i+1)%D,1,0,'1);
    $display("PASS {name} depth=%0d width=%0d 1R1W",D,W);
    done=1;
  end
endmodule
"""


def bench(mem, reference):
    if mem["read"]:
        return dual_bench(mem, reference)
    name, width, depth = mem["module_name"], mem["width"], mem["depth"]
    gran = mem.get("mask_granularity", width)
    lanes = width // gran
    mask_port = ", .RW0_wmask(mask)" if mem["masked"] else ""
    connections = (
        ".RW0_addr(addr), .RW0_clk(clk), .RW0_en(en), .RW0_wmode(wr), .RW0_wdata(data)"
    )
    return f"""
module test_{name}(output reg done = 0);
  localparam W={width}, D={depth}, G={gran}, M={lanes};
  reg clk=0;
  always #5 clk=~clk;
  reg [{(depth-1).bit_length()-1}:0] addr=0;
  reg en=0, wr=0;
  reg [W-1:0] data=0;
  reg [M-1:0] mask=0;
  wire [W-1:0] actual, reference;
  reg [W-1:0] model[0:D-1];
  integer seed=12345;
  {name} dut({connections}{mask_port}, .RW0_rdata(actual));
  {reference} original({connections}{mask_port}, .RW0_rdata(reference));
  task step(input integer a, input bit e, input bit w, input [M-1:0] m);
    reg [W-1:0] expected;
    begin
      @(negedge clk);
      addr=a; en=e; wr=w; mask=m;
      for (integer b=0; b<W; b=b+1) data[b]=$random(seed)&1;
      expected=model[a];
      @(posedge clk);
      #1;
      if (e && !w) begin
        if (actual !== expected || reference !== expected)
          $fatal(1, "{name}: read mismatch addr=%0d actual=%h ref=%h expected=%h",
                 a, actual, reference, expected);
        // Read data must not follow input addresses between rising edges.
        addr=(a+1)%D;
        #1;
        if (actual !== expected || reference !== expected)
          $fatal(1, "{name}: read latency changed");
      end
      if (e && w)
        for (integer lane=0; lane<M; lane=lane+1)
          if (m[lane] || {int(not mem['masked'])}) model[a][lane*G+:G]=data[lane*G+:G];
    end
  endtask
  initial begin
    for (integer a=0; a<D; a=a+1) step(a,1,1,{{M{{1'b1}}}});
    for (integer a=0; a<D; a=a+1) step(a,1,0,0);
    for (integer lane=0; lane<M; lane=lane+1) begin
      step(0,1,1,{{{{(M-1){{1'b0}}}},1'b1}}<<lane);
      step(0,1,0,0);
    end
    step(0,1,1,0);
    step(0,1,0,0);
    for (integer i=0; i<1000; i=i+1) begin
      step($unsigned($random(seed))%D,($random(seed)&3)!=0,$random(seed)&1,$random(seed));
    end
    for (integer a=0; a<D; a=a+1) step(a,0,1,{{M{{1'b1}}}});
    for (integer a=0; a<D; a=a+1) step(a,1,0,0);
    en=0; done=1;
    $display("PASS {name}: original RTL + scoreboard, full depth/mask/enable");
  end
endmodule
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--bound", type=Path, required=True)
    args = parser.parse_args()
    memories = json.loads((args.bound / "MEMORY_MANIFEST.json").read_text())["memories"]
    original = args.original.read_text()
    pieces = []
    for mem in memories:
        source, name = find_reference(original, mem)
        pieces.extend([source, bench(mem, name)])
    n = len(memories)
    pieces += [f"module tb; wire [{n-1}:0] done;"]
    pieces += [
        f"test_{m['module_name']} t{i}(done[{i}]);" for i, m in enumerate(memories)
    ]
    pieces += [
        'initial begin wait (&done); $display("PASS all memory bindings"); '
        "$finish; end",
        'initial begin #10000000; $fatal(1,"memory test timeout"); end',
        "endmodule",
    ]
    test = args.bound / "tb_memories.sv"
    test.write_text("`timescale 1ns/1ps\n" + "\n".join(pieces))
    output = args.bound / "tb_memories.vvp"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(output),
            str(args.bound / "FpgaMemories.sv"),
            str(test),
        ],
        check=True,
    )
    result = subprocess.run(
        ["vvp", str(output)], check=True, capture_output=True, text=True
    )
    (args.bound / "memory-test.log").write_text(result.stdout + result.stderr)
    print(result.stdout)
    assert "PASS all memory bindings" in result.stdout


if __name__ == "__main__":
    main()
