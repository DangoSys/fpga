"""真实 CPU→SCU 错误响应回归；记录异常行为，不把总线错误等同于同步 trap。"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import re
from offline_check import run_check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/board-mmio-error"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-file", type=Path, default=ROOT / "board/toy_a7_platform.sv")
    args = parser.parse_args()
    elf = OUT / "fault.elf"
    subprocess.run(["riscv64-unknown-elf-gcc", "-nostdlib", "-nostartfiles", "-mcmodel=medany",
                    "-march=rv64imafdc_zicsr_zifencei", "-mabi=lp64d", "-Wl,--no-relax",
                    "-T", str(ROOT / "tests/cpu_smoke.ld"), str(ROOT / "tests/mmio_error.S"), "-o", str(elf)], check=True)
    binary = OUT / "fault.bin"
    subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", str(elf), str(binary)], check=True)
    (OUT / "fault.hex").write_text("\n".join(f"{value:02x}" for value in binary.read_bytes()) + "\n")
    bench = (ROOT / "build/board-cpu/tb_board_cpu.sv").read_text().replace("tb_board_cpu", "tb_mmio_error")
    bench = bench.replace('"smoke.hex"', '"fault.hex"')
    bench = bench.replace('$display("PASS CPU', 'if(bad_b!=1 || bad_r!=1) $fatal(1,"Fault did not traverse AXI/SCU");\n      $display("PASS MMIO_ERROR CPU')
    bench = bench.replace("PASS MMIO_ERROR CPU Sv39/FPU/AMO/cache/interrupt through board AXI/SCU",
                          "PASS MMIO_ERROR CPU AXI/SCU response delivery")
    monitors = '''
  reg bad_write=0,bad_read=0;
  integer bad_b=0,bad_r=0;
  integer traps=-1;
  always @(posedge clk) if(!reset) begin
    if(exited && exit_code[31:16]==16'h7400 && traps<0) begin
      traps=exit_code[15:0];$display("MMIO_SYNCHRONOUS_TRAPS %0d",traps);
    end
    if(platform.peripherals_aw_valid && platform.peripherals_aw_ready)
      bad_write<=platform.peripherals_aw_bits_addr==31'h60030000;
    if(platform.peripherals_ar_valid && platform.peripherals_ar_ready)
      bad_read<=platform.peripherals_ar_bits_addr==31'h60030000;
    if(platform.peripherals_b_valid && platform.peripherals_b_ready && bad_write) begin
      if(platform.chip.peripherals_b_bits_resp!==2'b10) $fatal(1,"CPU did not receive SLVERR");
      bad_b<=bad_b+1;bad_write<=0;
    end
    if(platform.peripherals_r_valid && platform.peripherals_r_ready && bad_read) begin
      if(platform.chip.peripherals_r_bits_resp!==2'b10) $fatal(1,"CPU did not receive read error");
      bad_r<=bad_r+1;bad_read<=0;
    end
  end
'''
    bench = bench.replace("endmodule", monitors + "\nendmodule")
    path = OUT / "tb_mmio_error.sv"
    path.write_text(bench)
    sources = [ROOT / "build/serial-bound/ToyLinuxChip.sv", ROOT / "build/serial-bound/FpgaMemories.sv",
               ROOT / "tests/axi_smoke_memory.sv", path]
    sources += [args.platform_file if p.name=="toy_a7_platform.sv" else p
                for p in (ROOT / "board").glob("*.sv") if p.name != "toy_a7_top.sv"]
    with (OUT / "compile.log").open("w") as log:
        subprocess.run(["verilator", "--binary", "--timing", "-j", "4", "-Wno-fatal", "-DSYNTHESIS",
                        "-DBUCKYBALL_DISABLE_DPI", "--top-module", "tb_mmio_error", "--Mdir", str(OUT / "obj")]
                       + [str(p) for p in sources], stdout=log, stderr=log, check=True, timeout=900)
    result = subprocess.run([str(OUT / "obj/Vtb_mmio_error")], cwd=OUT, capture_output=True, text=True, timeout=180)
    (OUT / "simulation.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    if "PASS MMIO_ERROR CPU" not in result.stdout:
        raise ValueError("Missing CPU fault oracle")
    matches = re.findall(r"MMIO_SYNCHRONOUS_TRAPS (\d+)", result.stdout)
    if len(matches) != 1:
        raise ValueError("Missing synchronous-trap observation")
    record = {"result": "PASS_CPU_MMIO_SLVERR", "physical_hardware_tested": False,
              "synchronous_traps_observed": int(matches[0]), "synchronous_trap_guaranteed": False,
              "invalid_address": "0x60030000", "required_read_write_response": "10",
              "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
    (OUT / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(result.stdout)


if __name__ == "__main__":
    run_check(main, OUT)
