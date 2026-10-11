`timescale 1ns/1ps
module tb_axi_scu;
  reg clk=0;always #5 clk=~clk;
  reg reset=1;
  reg [1:0] awid=0,arid=0,awburst=1,arburst=1;
  reg [30:0] awaddr=0,araddr=0;
  reg [7:0] awlen=0,arlen=0;
  reg [2:0] awsize=0,arsize=0;
  reg awvalid=0,arvalid=0,wvalid=0,wlast=1,bready=0,rready=0;
  wire awready,arready,wready;
  reg [63:0] wdata=0;reg [7:0] wstrb=0;
  wire [1:0] bid,rid,bresp,rresp;
  wire bvalid,rvalid,rlast;wire [63:0] rdata;
  reg rx_valid=0,rx_error=0;reg [7:0] rx_data=0;
  wire tx_valid;wire [7:0] tx_data;reg tx_ready=0;
  wire exited,interrupt;wire [31:0] exit_code;
  integer tx_count=0;
  axi_scu dut(.*);
  always @(posedge clk) if(tx_valid && tx_ready) begin
    if(tx_data!==8'h53) $fatal(1,"SCU TX wrong lane/data");tx_count<=tx_count+1;
  end
  task automatic read_byte(input [30:0] addr,input [7:0] expected,input [1:0] resp);
    begin
      @(negedge clk);araddr=addr;arsize=0;arid=2;arvalid=1;
      do @(posedge clk);while(!arready);
      @(negedge clk);arvalid=0;
      while(!rvalid) @(negedge clk);
      repeat(5) begin
        if(rid!==2 || !rlast || rresp!==resp || (rdata>>(addr[2:0]*8) & 255)!==expected)
          $fatal(1,"SCU read addr=%h data=%h resp=%h",addr,rdata,rresp);
        @(negedge clk);
      end
      rready=1;@(negedge clk);rready=0;
    end
  endtask
  initial begin
    repeat(4) @(negedge clk);reset=0;
    @(negedge clk);rx_data=8'h71;rx_valid=1;@(negedge clk);rx_valid=0;
    read_byte(31'h60020005,1,0);
    if(!interrupt) $fatal(1,"RX IRQ missing");
    read_byte(31'h60020004,8'h71,0);
    if(interrupt) $fatal(1,"RX not popped exactly once");
    read_byte(31'h60020005,0,0);
    // A whole pasted command must survive a long interval between SBI polls.
    for(integer j=0;j<200;j=j+1) begin
      @(negedge clk);rx_data=j;rx_valid=1;@(negedge clk);rx_valid=0;
    end
    if(dut.overflow) $fatal(1,"FIFO overflow on a 200-byte paste");
    for(integer j=0;j<200;j=j+1) read_byte(31'h60020004,j[7:0],0);
    if(interrupt) $fatal(1,"FIFO not drained after paste");
    read_byte(31'h60030000,0,2);
    @(negedge clk);awaddr=31'h60020000;awid=3;awvalid=1;
    @(negedge clk);awvalid=0;wdata=64'h53;wstrb=1;wvalid=1;
    repeat(10) begin @(negedge clk);if(wready || bvalid) $fatal(1,"SCU lost TX backpressure");end
    tx_ready=1;@(negedge clk);wvalid=0;
    repeat(4) @(negedge clk);
    if(!bvalid || bid!==3 || bresp!==0 || tx_count!=1) $fatal(1,"SCU TX response/count");
    bready=1;@(negedge clk);bready=0;
    awaddr=31'h60000000;awsize=2;awvalid=1;@(negedge clk);awvalid=0;
    wdata=64'h12345678;wstrb=15;wvalid=1;@(negedge clk);wvalid=0;
    if(!exited || exit_code!==32'h12345678) $fatal(1,"SCU EXIT decode");
    $display("PASS SCU OpenSBI byte addresses, AXI lanes, RX pop/IRQ, TX backpressure, EXIT");$finish;
  end
  initial begin #100000;$fatal(1,"SCU watchdog");end
endmodule
