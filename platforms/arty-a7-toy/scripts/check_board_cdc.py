"""Exercise the actual Xilinx AXI Clock Converter with the adapter oracle.

The MIG PHY is replaced by the stalled memory model. The converter uses the
same generated IP as the specified board build, copied into a test directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board_run")
    parser.add_argument("--output-name", default="board-cdc")
    args = parser.parse_args()
    source = ROOT / "build" / args.board_run / "ip/toy_axi_cdc"
    assert source.is_dir(), source
    assert re.fullmatch(r"board-cdc(?:-[a-zA-Z0-9-]+)?", args.output_name)
    out = ROOT / "build" / args.output_name
    out.mkdir(parents=True, exist_ok=True)
    ip = out / "ip/toy_axi_cdc"
    assert not ip.exists(), "Keep previous simulation evidence; use a fresh output"
    shutil.copytree(source, ip)

    bench = (ROOT / "tests/tb_axi_fullwidth.sv").read_text()
    bench = bench.replace("tb_axi_fullwidth", "tb_board_cdc")
    bench = bench.replace("always #5 clk=~clk;", "always #20 clk=~clk;\n  reg ui_clk=0; initial begin #3; forever #6 ui_clk=~ui_clk; end")
    # Reuse exactly the board's converter instance and port tie-offs.
    top = (ROOT / "board/toy_a7_top.sv").read_text()
    declarations = top[top.index("  wire [3:0] ui_awid;"):top.index("  toy_a7_platform platform")]
    instance = top[top.index("  toy_axi_cdc memory_cdc"):top.index("  arty_ddr3 ddr_controller")]
    instance = instance.replace("ddr_", "m_").replace("ui_aresetn", "!reset")
    bench = bench.replace("  axi_fullwidth dut(.*);", declarations + instance + "  axi_fullwidth dut(.*);")
    first = bench.index("  axi_smoke_memory")
    last = bench.index("  always @(posedge clk)", first)
    memory = bench[first:last].replace(".clock(clk)", ".clock(ui_clk)").replace("(m_", "(ui_")
    bench = bench[:first] + memory + bench[last:]
    bench = bench.replace("repeat(5) @(negedge clk);reset=0;", "repeat(20) @(negedge clk);reset=0;repeat(60) @(negedge clk);")
    bench = bench.replace("PASS fullwidth AXI:", "PASS BOARD_CDC:")
    bench = bench.replace("#2000000", "#10000000")
    (out / "tb_board_cdc.sv").write_text(bench)
    tcl = f"""create_project -force cdc_test {{{out / 'project'}}} -part xc7a100tcsg324-1
read_ip {{{ip / 'toy_axi_cdc.xci'}}}
read_verilog -sv {{{ROOT / 'board/axi_fullwidth.sv'}}}
read_verilog -sv {{{ROOT / 'tests/axi_smoke_memory.sv'}}}
read_verilog -sv {{{out / 'tb_board_cdc.sv'}}}
set_property top tb_board_cdc [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
exit
"""
    script = out / "simulate.tcl"
    script.write_text(tcl)
    with (out / "console.log").open("w") as log:
        result = subprocess.run([os.environ.get("VIVADO", "vivado"), "-mode", "batch", "-source", str(script),
                                 "-log", str(out / "vivado.log"), "-journal", str(out / "vivado.jou")],
                                cwd=out, stdout=log, stderr=log, timeout=900)
    result.check_returncode()
    simulation = out / "project/cdc_test.sim/sim_1/behav/xsim/simulate.log"
    transcript = simulation.read_text()
    assert "PASS BOARD_CDC:" in transcript, transcript[-2000:]
    record = dict(result="PASS_BOARD_CDC", board_run=args.board_run,
                  core_clock_hz=25000000, ui_clock_hz=83333333,
                  read_beats=90, physical_mig_simulated=False,
                  xci_sha256=hashlib.sha256((ip / "toy_axi_cdc.xci").read_bytes()).hexdigest(),
                  bench_sha256=hashlib.sha256(bench.encode()).hexdigest())
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(transcript[-1600:])


if __name__ == "__main__":
    main()
