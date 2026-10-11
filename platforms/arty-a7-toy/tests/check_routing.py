"""Exercise fixed routes using the real AccPipe and delayed SRAM responses."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "build/routing-check"
rtl = out / "RoutingCheck.sv"
tb = out / "tb.sv"
tb.write_text(
    """`timescale 1ns/1ps
module tb;
  reg clock=0, reset=1;
  wire passed;
  RoutingCheck dut(.*);
  always #5 clock=~clock;
  initial begin
    repeat(10) @(negedge clock);
    reset=0;
    wait(passed);
    $display("PASS fixed routing: 512 transactions, DMA arbitration, stalls");
    $finish;
  end
  initial begin
    repeat(20000) @(posedge clock);
    $fatal(1, "Routing check timeout");
  end
endmodule
"""
)
subprocess.run(
    [
        "verilator",
        "--binary",
        "--timing",
        "--assert",
        "-j",
        "8",
        "-Wno-fatal",
        "--top-module",
        "tb",
        "--Mdir",
        str(out / "obj"),
        str(rtl),
        str(tb),
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
result = subprocess.run([str(out / "obj/Vtb")], capture_output=True, text=True)
(out / "simulation.log").write_text(result.stdout + result.stderr)
print(result.stdout)
assert result.returncode == 0 and "PASS fixed routing" in result.stdout
(out / "RESULT.json").write_text(
    json.dumps(
        {
            "result": "PASS",
            "transactions": 512,
            "coverage": [
                "two Gemmini reads",
                "four Gemmini writes",
                "concurrent DMA requests",
                "request stalls",
                "response stalls",
                "backend route look-ahead",
                "opposite-direction request arriving during pending route",
                "Ball release with responses pending",
            ],
            "rtl_sha256": hashlib.sha256(rtl.read_bytes()).hexdigest(),
        },
        indent=2,
    )
    + "\n"
)
