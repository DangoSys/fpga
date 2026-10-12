"""Boot OpenSBI/Linux/BusyBox on the actual core and board AXI/SCU RTL.

The external DDR PHY/CDC is a stalled AXI memory model. Loader start is forced
only in this bench; commands enter through the real 1 Mbps UART receiver.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build/board-linux-final"


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    payload=ROOT/"build/board-software/fw_payload.bin"
    # Chunked writes avoid creating a giant intermediate Python string.
    with payload.open("rb") as src,(OUT/"payload.hex").open("w") as dst:
        while data:=src.read(65536):dst.write("\n".join(f"{b:02x}" for b in data)+"\n")
    bench=(ROOT/"build/board-cpu/tb_board_cpu.sv").read_text()
    bench=bench.replace("tb_board_cpu","tb_board_linux")
    bench=bench.replace("always #5 clk=~clk;", "always #20 clk=~clk;")
    first=bench.index("    if(exited &&")
    last=bench.index("  end\n  axi_smoke_memory",first)
    bench=bench[:first]+"    if(cycles>500000000) $fatal(1,\"Linux cycle watchdog\");\n"+bench[last:]
    bench=bench.replace(".CAPACITY(262144)",".CAPACITY(268435456)")
    bench=bench.replace('"smoke.hex"','"payload.hex"')
    console='''
  reg [255:0] tail=0;
  reg init_seen=0,prompt_seen=0;
  integer characters=0;
  always @(posedge clk) if(!reset && platform.mmio_tx_valid && platform.tx_ready && cpu_run) begin
    tail={tail[247:0],platform.mmio_tx_data};characters=characters+1;
    $write("%c",platform.mmio_tx_data);$fflush();
    if(tail[95:0]=="init process") init_seen=1;
    if(init_seen && tail[15:0]==16'h2320) prompt_seen=1;
    if(tail[183:0]=="PASS LINUX_SYSTEM_CHECK") begin
      $display("\\nPASS BOARD_LINUX_USERSPACE cycles=%0d characters=%0d",cycles,characters);$finish;
    end
    if(tail[95:0]=="Kernel panic") $fatal(1,"Kernel panic");
  end
  task automatic send_byte(input [7:0] value);
    @(negedge clk);uart_rx_in=0;repeat(25) @(negedge clk);
    for(integer n=0;n<8;n=n+1) begin uart_rx_in=value[n];repeat(25) @(negedge clk);end
    uart_rx_in=1;repeat(25) @(negedge clk);
    // Allow the polled SBI/HVC console to drain its RAM-backed RX FIFO.
    repeat(250000) @(negedge clk);
  endtask
  initial begin
    wait(prompt_seen);
    $display("\\nSIM_SHELL_PROMPT cycles=%0d",cycles);$fflush();
    send_byte("/");send_byte("r");send_byte("o");send_byte("o");send_byte("t");send_byte("/");
    send_byte("l");send_byte("i");send_byte("n");send_byte("u");send_byte("x");send_byte("_");
    send_byte("s");send_byte("y");send_byte("s");send_byte("t");send_byte("e");send_byte("m");send_byte("_");
    send_byte("c");send_byte("h");send_byte("e");send_byte("c");send_byte("k");send_byte("-");
    send_byte("l");send_byte("i");send_byte("n");send_byte("u");send_byte("x");send_byte(10);
    $display("\\nSIM_COMMAND_SENT cycles=%0d overflow=%0d framing=%0d pending_rx=%0d",cycles,
      platform.peripherals.overflow,platform.peripherals.framing,platform.peripherals.count);$fflush();
    if(platform.peripherals.overflow || platform.peripherals.framing) $fatal(1,"UART input loss");
  end
'''
    bench=bench.replace("endmodule",console+"\nendmodule")
    path=OUT/"tb_board_linux.sv"
    path.write_text(bench)
    files=[ROOT/"build/serial-bound/ToyLinuxChip.sv",ROOT/"build/serial-bound/FpgaMemories.sv",
           ROOT/"tests/axi_smoke_memory.sv",path]+[p for p in (ROOT/"board").glob("*.sv") if p.name!="toy_a7_top.sv"]
    with (OUT/"compile.log").open("w") as log:
        subprocess.run(["verilator","--binary","--timing","-j","8","-Wno-fatal","-DSYNTHESIS",
                        "-DBUCKYBALL_DISABLE_DPI","--top-module","tb_board_linux","--Mdir",str(OUT/"obj")]+[str(p) for p in files],
                       stdout=log,stderr=log,check=True,timeout=900)
    with (OUT/"simulation.log").open("w") as log:
        result=subprocess.run([str(OUT/"obj/Vtb_board_linux")],cwd=OUT,stdout=log,stderr=log,timeout=3000)
    transcript=(OUT/"simulation.log").read_text()
    result.check_returncode()
    required=["OpenSBI","Linux version","PASS VM_COPY_ON_WRITE","PASS VM_PAGE_PROTECTION",
              "PASS FP64_PROCESS_CONTEXT","PASS LINUX_TIMER","PASS LINUX_SYSTEM_CHECK","PASS BOARD_LINUX_USERSPACE"]
    for marker in required:assert marker in transcript,marker
    record=dict(result="PASS_RTL_LINUX_USERSPACE",payload_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),
                checks=required,physical_mig_simulated=False,physical_board_tested=False,uart_rx_command_tested=True)
    (OUT/"RESULT.json").write_text(json.dumps(record,indent=2)+"\n")
    print(transcript[-2000:])


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/"RESULT.json").write_text(json.dumps(dict(result="FAIL",error=str(error),physical_board_tested=False),indent=2)+"\n")
        raise
