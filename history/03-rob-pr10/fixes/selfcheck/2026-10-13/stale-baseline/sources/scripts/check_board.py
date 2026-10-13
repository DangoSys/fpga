"""Test the exact board loader, AXI normalizer and OpenSBI SCU with stalls."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build/board-unit"


def run(name, files, marker):
    executable=OUT/name
    command=["iverilog","-g2012","-s",name,"-o",str(executable)]+[str(f) for f in files]
    compiled=subprocess.run(command,capture_output=True,text=True,timeout=60)
    (OUT/(name+"-compile.log")).write_text(compiled.stdout+compiled.stderr)
    compiled.check_returncode()
    result=subprocess.run(["vvp",str(executable)],capture_output=True,text=True,timeout=60)
    (OUT/(name+".log")).write_text(result.stdout+result.stderr)
    print(result.stdout,end="")
    result.check_returncode()
    assert marker in result.stdout


def main():
    fixture=json.loads((ROOT/"tests/PLATFORM_PORTS_MANIFEST.json").read_text())
    if hashlib.sha256((ROOT/"tests/ToyLinuxChipPorts.sv").read_bytes()).hexdigest()!=fixture["stub_sha256"]:
        raise ValueError("CPU port fixture differs from its manifest")
    OUT.mkdir(parents=True,exist_ok=True)
    run("tb_axi_fullwidth",[ROOT/"board/axi_fullwidth.sv",ROOT/"tests/axi_smoke_memory.sv",ROOT/"tests/tb_axi_fullwidth.sv"],"PASS fullwidth AXI")
    run("tb_axi_scu",[ROOT/"board/axi_scu.sv",ROOT/"tests/tb_axi_scu.sv"],"PASS SCU")
    platform_files=[ROOT/"board"/name for name in
                    ("toy_a7_platform.sv","axi_fullwidth.sv","axi_scu.sv","ddr_uart_loader.sv",
                     "loader_axi.sv","uart_rx.sv","uart_tx.sv","flash_spi_byte.sv")]
    run("tb_platform_bresp",platform_files+[ROOT/"tests/ToyLinuxChipPorts.sv",ROOT/"tests/tb_platform_bresp.sv"],
        "PASS platform AXI B response")
    # Retain the CRC/range/timeout/rejected RUN oracle from the earlier loader,
    # but connect its new acknowledgement boundary to AXI, not zero-latency RAM.
    template=(ROOT/"tests/board_loader_template.sv").read_text()
    template=template.replace("module tb_uart_loader", "module tb_ddr_loader")
    template=template.replace("uart_loader #", "ddr_uart_loader #")
    template=template.replace("32'h01374150", "32'h02374154")
    template=template.replace("axi_bram #(.WORDS(256)) memory(", "/* legacy memory removed\naxi_bram #(.WORDS(256)) memory(")
    template=template.replace("  always @(posedge clk) begin\n", "*/\n"+LOADER_MEMORY+"\n  always @(posedge clk) begin\n",1)
    template=template.replace("wire cpu_run,error_seen,load_en,load_valid;", "wire cpu_run,error_seen,load_en,load_valid,load_error;")
    template=template.replace("PASS: UART loader", "PASS: DDR UART loader")
    (OUT/"tb_ddr_loader.sv").write_text(template)
    run("tb_ddr_loader",[ROOT/"board/ddr_uart_loader.sv",ROOT/"board/loader_axi.sv",ROOT/"tests/axi_smoke_memory.sv",OUT/"tb_ddr_loader.sv"],"PASS: DDR UART loader")
    files=[p for p in (ROOT/"board").glob("*.sv")]+[ROOT/"tests/tb_axi_fullwidth.sv",ROOT/"tests/tb_axi_scu.sv"]
    files += [ROOT/"tests/ToyLinuxChipPorts.sv",ROOT/"tests/tb_platform_bresp.sv"]
    record=dict(result="PASS",tests=4,physical_mig_simulated=False,
                sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (OUT/"RESULT.json").write_text(json.dumps(record,indent=2)+"\n")


LOADER_MEMORY="""
  wire [27:0] awaddr,araddr;
  wire awvalid,wvalid,arvalid,bready,rready,awready,wready,arready,bvalid,rvalid;
  wire [127:0] wdata,rdata;
  wire [15:0] wstrb;
  wire [1:0] bresp,rresp;
  loader_axi bridge(.clk(clk),.reset(reset),.load_en(load_en),.load_addr({16'd0,load_addr}),
    .load_data(load_data),.load_mask(load_mask),.load_valid(load_valid),.load_error(load_error),.load_result(load_result),
    .awaddr(awaddr),.araddr(araddr),.awvalid(awvalid),.wvalid(wvalid),.arvalid(arvalid),
    .bready(bready),.rready(rready),.awready(awready),.wready(wready),.arready(arready),
    .bvalid(bvalid),.rvalid(rvalid),.wdata(wdata),.wstrb(wstrb),.bresp(bresp),.rresp(rresp),.rdata(rdata));
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(4096)) memory (
    .clock(clk),.reset(reset),.aw_bits_id(4'd0),.aw_bits_addr(awaddr),.aw_bits_len(8'd0),.aw_bits_size(3'd4),.aw_bits_burst(2'd1),
    .aw_valid(awvalid),.aw_ready(awready),.w_bits_data(wdata),.w_bits_strb(wstrb),.w_bits_last(1'b1),.w_valid(wvalid),.w_ready(wready),
    .b_ready(bready),.b_valid(bvalid),.b_bits_id(),.b_bits_resp(bresp),
    .ar_bits_id(4'd0),.ar_bits_addr(araddr),.ar_bits_len(8'd0),.ar_bits_size(3'd4),.ar_bits_burst(2'd1),.ar_valid(arvalid),.ar_ready(arready),
    .r_ready(rready),.r_valid(rvalid),.r_bits_id(),.r_bits_data(rdata),.r_bits_resp(rresp),.r_bits_last());
"""


if __name__=="__main__":
    main()
