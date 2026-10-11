"""Prove the quantizer and compare original/LUT/DSP PEs cycle by cycle."""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rtl(path):
    data = path.read_text()
    marker = '// ----- 8< ----- FILE "firrtl_black_box_resource_files.f" ----- 8< -----'
    if marker in data:
        data, filelist = data.split(marker)
        assert all(x.strip().endswith(".v") for x in filelist.splitlines() if x.strip())
    output = path.with_name(path.stem + "_rtl.sv")
    output.write_text(data)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosys", default="yosys")
    args = parser.parse_args()
    out = ROOT / "build/pe-checks"
    quant = rtl(out / "quantizer/QuantizerEquivalence.sv")
    command = (
        f"read_verilog -sv {quant}; prep -top QuantizerEquivalence -flatten; "
        "sat -prove equal 1 -verify -show-inputs -show-outputs"
    )
    with (out / "quantizer-proof.log").open("w") as log:
        subprocess.run(
            [args.yosys, "-p", command], stdout=log, stderr=log, check=True, timeout=180
        )
    cycles = rtl(out / "cycles/PeCycleEquivalence.sv")
    bench = out / "tb_pe.sv"
    bench.write_text(
        """
`timescale 1ns/1ps
module tb;
  reg clock=0;
  always #5 clock=~clock;
  reg reset=0;
  reg [7:0] in_a=0;
  reg [19:0] in_b=0, in_d=0;
  reg control_dataflow=0, control_propagate=0;
  reg [4:0] control_shift=0;
  reg [1:0] id=0;
  reg last=0, valid=1;
  wire equal;
  integer checked=0;
  integer seed=57201;
  PeCycleEquivalence dut(.*);
  task step(input bit df, input bit prop, input integer shift,
            input integer a, input integer b, input integer d,
            input bit v, input bit check);
    begin
      @(negedge clock);
      control_dataflow=df; control_propagate=prop; control_shift=shift;
      in_a=a; in_b=b; in_d=d; valid=v;
      id=$random(seed); last=$random(seed);
      #1;
      if (check && v) begin
        if (equal !== 1'b1) begin
          $display("PE mismatch df=%0d prop=%0d shift=%0d",df,prop,shift);
          $fatal(1,"a=%0d b=%0d d=%0d cycle=%0d",a,b,d,checked);
        end
        checked=checked+1;
      end
      @(posedge clock); #1;
    end
  endtask
  initial begin
    // Initialize both original accumulator registers through legal loading.
    step(0,1,0,0,0,0,1,0);
    step(0,0,0,0,0,0,1,0);
    for (integer shift=0; shift<32; shift=shift+1)
      for (integer df=0; df<2; df=df+1)
        for (integer p=0; p<2; p=p+1)
          for (integer n=0; n<16; n=n+1) begin
            step(df,p,shift,(n&1)?-128:127,(n&2)?-524288:524287,
                 (n&4)?-524288:524287,1,1);
            step(df,!p,shift,(n&1)?-1:1,(n&2)?-3:3,(n&4)?-1:1,1,1);
            step(df,p,shift,0,0,0,0,1);
          end
    for (integer n=0; n<100000; n=n+1)
      step($random(seed)&1,$random(seed)&1,$random(seed)&31,
           $random(seed),$random(seed),$random(seed),($random(seed)&7)!=0,1);
    $display("PASS original/LUT/DSP PE: %0d valid-cycle comparisons",checked);
    $finish;
  end
  initial begin #2000000; $fatal(1,"PE test timeout"); end
endmodule
"""
    )
    obj = out / "obj"
    with (out / "verilator-build.log").open("w") as log:
        subprocess.run(
            [
                "verilator",
                "--binary",
                "--timing",
                "-j",
                "8",
                "-Wno-fatal",
                "-DSYNTHESIS",
                "--top-module",
                "tb",
                "--Mdir",
                str(obj),
                str(cycles),
                str(bench),
            ],
            stdout=log,
            stderr=log,
            check=True,
            timeout=180,
        )
    result = subprocess.run(
        [str(obj / "Vtb")], capture_output=True, text=True, check=True, timeout=120
    )
    (out / "cycles-test.log").write_text(result.stdout + result.stderr)
    assert "PASS original/LUT/DSP PE" in result.stdout
    print("PASS formal quantizer equivalence for all 2^25 input/shift pairs")
    print(result.stdout)


if __name__ == "__main__":
    main()
