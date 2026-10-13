`timescale 1ns/1ps
module tb_platform_bresp;
  reg clk=0;
  always #5 clk=~clk;
  reg reset=1;
  reg [30:0] address=0;
  reg [2:0] size=2;
  reg [7:0] length=0;
  reg awvalid=0,wvalid=0,last=1,bready=0;
  toy_a7_platform dut(.clk(clk),.reset(reset),.uart_rx_in(1'b1),
    .ddr_awready(1'b1),.ddr_wready(1'b1),.ddr_bid(4'd0),.ddr_bresp(2'd0),.ddr_bvalid(1'b0),
    .ddr_arready(1'b1),.ddr_rid(4'd0),.ddr_rdata(128'd0),.ddr_rresp(2'd0),.ddr_rlast(1'b1),.ddr_rvalid(1'b0),
    .flash_miso(1'b0),.flash_recovery(1'b0));
  task automatic write_case(input [30:0] addr,input [2:0] width,input [7:0] len,input [1:0] expected);
    @(negedge clk);address=addr;size=width;length=len;awvalid=1;
    do @(posedge clk);while(!dut.peripherals_aw_ready);
    @(negedge clk);awvalid=0;
    for(integer beat=0;beat<=len;beat=beat+1) begin
      wvalid=1;last=beat==len;
      do @(posedge clk);while(!dut.peripherals_w_ready);
      @(negedge clk);wvalid=0;
    end
    while(!dut.peripherals_b_valid) @(negedge clk);
    repeat(5) begin
      // Observe the CPU input, through actual platform wiring and real SCU.
      if(dut.chip.peripherals_b_valid!==1 || dut.chip.peripherals_b_bits_resp!==expected ||
         dut.chip.peripherals_b_bits_id!==2)
        $fatal(1,"Platform B response addr=%h valid=%b id=%b actual=%b expected=%b",addr,
          dut.chip.peripherals_b_valid,dut.chip.peripherals_b_bits_id,dut.chip.peripherals_b_bits_resp,expected);
      @(negedge clk);
    end
    bready=1;@(negedge clk);bready=0;
    if(dut.chip.peripherals_b_valid!==0) $fatal(1,"BVALID not cleared after handshake");
  endtask
  initial begin
    force dut.cpu_run=1;
    force dut.peripherals_aw_valid=awvalid;
    force dut.peripherals_aw_bits_addr=address;
    force dut.peripherals_aw_bits_size=size;
    force dut.peripherals_aw_bits_len=length;
    force dut.peripherals_aw_bits_id=2;
    force dut.peripherals_aw_bits_burst=1;
    force dut.peripherals_w_valid=wvalid;
    force dut.peripherals_w_bits_last=last;
    force dut.peripherals_w_bits_data=64'h13572468;
    force dut.peripherals_w_bits_strb=8'h0f;
    force dut.peripherals_b_ready=bready;
    repeat(5) @(negedge clk);reset=0;
    write_case(31'h60000000,2,0,0);
    if(!dut.exited || dut.exit_code!==32'h13572468) $fatal(1,"Valid MMIO changed");
    write_case(31'h60030000,2,0,2);
    write_case(31'h60000002,2,0,2);
    write_case(31'h60000000,2,1,2);
    $display("PASS platform AXI B response: valid, invalid address, unaligned, burst, ID and backpressure");
    $finish;
  end
  initial begin #100000;$fatal(1,"Platform response watchdog");end
endmodule
