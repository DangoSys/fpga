"""Load, byte-verify and boot the original CPU oracle through actual UART RTL.

Only the external DDR PHY is replaced with the stalled AXI memory model. No
testbench override releases the CPU and no initial image is put into DDR.
"""
import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/board-uart-boot"

UART = r'''
  reg [7:0] firmware[0:PROGRAM_BYTES-1];
  reg [7:0] reply_bytes[0:511];
  integer received=0;
  reg run_requested=0;
  initial $readmemh("program.hex",firmware);
  // Independent receiver observes real TX transitions, not tx_valid/data.
  always begin : receiver
    reg [7:0] value;
    @(negedge uart_tx_out);
    repeat(37) @(negedge clk);
    for(integer bit_index=0;bit_index<8;bit_index=bit_index+1) begin
      value[bit_index]=uart_tx_out;repeat(25) @(negedge clk);
    end
    if(uart_tx_out!==1) $fatal(1,"UART TX framing error");
    if(!cpu_run) begin
      if(received>=512) $fatal(1,"UART reply overflow");
      reply_bytes[received]=value;received=received+1;
    end
  end
  always @(posedge clk) if(!reset && cpu_run && !run_requested)
    $fatal(1,"CPU released before verified RUN request");
  function automatic [15:0] crc_step(input [15:0] previous,input [7:0] value);
    reg [15:0] crc;
    begin
      crc=previous;
      for(integer bit_index=7;bit_index>=0;bit_index=bit_index-1)
        crc=(crc<<1)^((crc[15]^value[bit_index]) ? 16'h1021 : 16'd0);
      crc_step=crc;
    end
  endfunction
  task automatic send_byte(input [7:0] value);
    @(negedge clk);uart_rx_in=0;repeat(25) @(negedge clk);
    for(integer bit_index=0;bit_index<8;bit_index=bit_index+1) begin
      uart_rx_in=value[bit_index];repeat(25) @(negedge clk);
    end
    uart_rx_in=1;repeat(25) @(negedge clk);
  endtask
  task automatic request(input [7:0] op,input integer offset,length,input bit corrupt);
    reg [15:0] crc;reg [31:0] address;reg [7:0] value;
    begin
      received=0;crc=16'hffff;address=32'h80000000+offset;
      send_byte(8'ha5);send_byte(8'h5a);
      send_byte(op);crc=crc_step(crc,op);
      send_byte(8'h37);crc=crc_step(crc,8'h37);
      for(integer n=0;n<4;n=n+1) begin
        value=address>>(8*n);send_byte(value);crc=crc_step(crc,value);
      end
      value=length&255;send_byte(value);crc=crc_step(crc,value);
      value=(length>>8)&255;send_byte(value);crc=crc_step(crc,value);
      if(op==1) for(integer n=0;n<length;n=n+1) begin
        value=firmware[offset+n];send_byte(value);crc=crc_step(crc,value);
      end
      send_byte(crc[7:0]^(corrupt ? 8'h01 : 8'h00));send_byte(crc[15:8]);
    end
  endtask
  task automatic reply(input [7:0] op,status,input integer length);
    reg [15:0] crc;
    begin
      wait(received>=length+9);
      if(reply_bytes[0]!==8'h5a || reply_bytes[1]!==8'ha5 || reply_bytes[2]!==(op|8'h80) ||
         reply_bytes[3]!==8'h37 || reply_bytes[4]!==status || {reply_bytes[6],reply_bytes[5]}!==length)
        $fatal(1,"UART reply header/status op=%h status=%h count=%0d",op,reply_bytes[4],received);
      crc=16'hffff;
      for(integer n=2;n<length+7;n=n+1) crc=crc_step(crc,reply_bytes[n]);
      if({reply_bytes[length+8],reply_bytes[length+7]}!==crc) $fatal(1,"UART reply CRC");
      repeat(40) @(negedge clk);
    end
  endtask
  initial begin : host
    integer count;
    wait(!reset);repeat(50) @(negedge clk);
    request(3,0,0,0);reply(3,5,0);
    request(1,0,16,1);reply(1,1,0);
    for(integer offset=0;offset<PROGRAM_BYTES;offset=offset+256) begin
      count=PROGRAM_BYTES-offset; if(count>256) count=256;
      request(1,offset,count,0);reply(1,0,0);
      request(2,offset,count,0);reply(2,0,count);
      for(integer n=0;n<count;n=n+1) if(reply_bytes[7+n]!==firmware[offset+n])
        $fatal(1,"UART DDR readback byte %0d",offset+n);
    end
    $display("PASS UART_PAYLOAD_READBACK bytes=%0d cycles=%0d",PROGRAM_BYTES,cycles);
    request(3,0,0,1);reply(3,1,0);
    if(cpu_run) $fatal(1,"Corrupt RUN released CPU");
    run_requested=1;request(3,0,0,0);reply(3,0,0);
    wait(cpu_run);
    $display("PASS UART_VERIFIED_RUN cycles=%0d",cycles);
  end
'''


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flash-recovery",action="store_true",help="Use the new ROM with SW0 recovery selected")
    args=parser.parse_args()
    if args.flash_recovery:
        OUT=ROOT/"build/board-uart-flash-recovery"
    OUT.mkdir(parents=True, exist_ok=True)
    binary = ROOT / "build/cpu-smoke/smoke.bin"
    data = binary.read_bytes()
    (OUT / "program.hex").write_text("\n".join(f"{byte:02x}" for byte in data) + "\n")
    bench = (ROOT / "build/board-cpu/tb_board_cpu.sv").read_text()
    bench = bench.replace("tb_board_cpu", "tb_board_uart_boot")
    bench = bench.replace("always #5 clk=~clk;", "always #20 clk=~clk;")
    bench = bench.replace("force platform.loader.cpu_run=1;", "")
    if args.flash_recovery:
        bench=bench.replace("toy_a7_platform platform(.*);", "toy_a7_platform #(.FLASH_BOOT(1)) platform(.*);")
        bench=bench.replace("wire flash_recovery;", "wire flash_recovery=1;")
        bench=bench.replace("wire flash_miso;", "wire flash_miso=0;")
        bench=bench.replace(".CAPACITY(262144)", ".CAPACITY(268435456)")
    bench = bench.replace('.IMAGE("smoke.hex")', '.IMAGE("")')
    bench = bench.replace("cycles>4000000", "cycles>120000000")
    bench = bench.replace("endmodule", f"  localparam PROGRAM_BYTES={len(data)};\n" + UART + "\nendmodule")
    path = OUT / "tb_board_uart_boot.sv"
    path.write_text(bench)
    core=ROOT/("build/flash-boot/ToyLinuxChip.sv" if args.flash_recovery else "build/serial-bound/ToyLinuxChip.sv")
    files = [core, ROOT / "build/serial-bound/FpgaMemories.sv",
             ROOT / "tests/axi_smoke_memory.sv", path]
    files += [p for p in (ROOT / "board").glob("*.sv") if p.name != "toy_a7_top.sv"]
    with (OUT / "compile.log").open("w") as log:
        subprocess.run(["verilator", "--binary", "--timing", "-j", "8", "-Wno-fatal", "-DSYNTHESIS",
                        "-DBUCKYBALL_DISABLE_DPI", "--top-module", "tb_board_uart_boot", "--Mdir", str(OUT / "obj")]
                       + [str(p) for p in files], stdout=log, stderr=log, check=True, timeout=900,cwd=ROOT)
    if args.flash_recovery:
        # The bound ROM's readmemh path is relative to the platform directory.
        import shutil
        (OUT/"build/flash-boot").mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/"build/flash-boot/bootrom.hex",OUT/"build/flash-boot/bootrom.hex")
    with (OUT / "simulation.log").open("w") as log:
        result = subprocess.run([str(OUT / "obj/Vtb_board_uart_boot")], cwd=OUT,
                                stdout=log, stderr=log, timeout=1200)
    result.check_returncode()
    transcript = (OUT / "simulation.log").read_text()
    for marker in ("PASS UART_PAYLOAD_READBACK", "PASS UART_VERIFIED_RUN", "PASS CPU Sv39/FPU/AMO/cache/interrupt"):
        assert marker in transcript, marker
    record = dict(result="PASS_UART_LOAD_VERIFY_BOOT", binary_sha256=hashlib.sha256(data).hexdigest(),
                  bytes_verified=len(data), testbench_cpu_release_override=False, preloaded_ddr_image=False,
                  physical_mig_simulated=False, physical_board_tested=False,
                  flash_rom_recovery=args.flash_recovery,
                  cycles=int(re.search(r"through board AXI/SCU cycles=(\d+)", transcript)[1]))
    (OUT / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(transcript)


if __name__ == "__main__":
    main()
