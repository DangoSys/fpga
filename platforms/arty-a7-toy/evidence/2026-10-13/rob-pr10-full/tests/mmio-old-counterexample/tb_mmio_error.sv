`timescale 1ns/1ps
module tb_mmio_error;
  reg clk=0;always #5 clk=~clk;
  reg reset=1,uart_rx_in=1;
  wire uart_tx_out;
  wire cpu_run;
  wire exited;
  wire loader_error;
  wire [31:0] exit_code;
  wire [3:0] ddr_awid;
  wire [27:0] ddr_awaddr;
  wire [7:0] ddr_awlen;
  wire [2:0] ddr_awsize;
  wire [1:0] ddr_awburst;
  wire ddr_awvalid;
  wire ddr_awready;
  wire [127:0] ddr_wdata;
  wire [15:0] ddr_wstrb;
  wire ddr_wlast;
  wire ddr_wvalid;
  wire ddr_wready;
  wire [3:0] ddr_bid;
  wire [1:0] ddr_bresp;
  wire ddr_bvalid;
  wire ddr_bready;
  wire [3:0] ddr_arid;
  wire [27:0] ddr_araddr;
  wire [7:0] ddr_arlen;
  wire [2:0] ddr_arsize;
  wire [1:0] ddr_arburst;
  wire ddr_arvalid;
  wire ddr_arready;
  wire [3:0] ddr_rid;
  wire [127:0] ddr_rdata;
  wire [1:0] ddr_rresp;
  wire ddr_rlast;
  wire ddr_rvalid;
  wire ddr_rready;
  wire flash_miso;
  wire flash_recovery;
  wire flash_mosi;
  wire flash_sck;
  wire flash_cs_n;
  toy_a7_platform platform(.*);
  initial begin
    repeat(10) @(negedge clk); force platform.loader.cpu_run=1;reset=0;end
  integer cycles=0;
  always @(posedge clk) if(!reset) begin
    cycles<=cycles+1;
    if(platform.memory_aw_valid && platform.memory_aw_bits_lock) $fatal(1,"Unexpected AXI exclusive write");
    if(platform.memory_ar_valid && platform.memory_ar_bits_lock) $fatal(1,"Unexpected AXI exclusive read");
    if(ddr_awvalid && ddr_awready && (ddr_awsize!=4 || ddr_awlen!=0)) $fatal(1,"Narrow DDR write");
    if(ddr_arvalid && ddr_arready && (ddr_arsize!=4 || ddr_arlen!=0)) $fatal(1,"Narrow DDR read");
    if(exited && (exit_code & 32'hffff0000)==32'hbad00000) $fatal(1,"CPU oracle failed stage=%h",exit_code);
    if(exited && exit_code==32'h600d600d) begin
      if(bad_b!=1 || bad_r!=1) $fatal(1,"Fault did not traverse AXI/SCU");
      $display("PASS MMIO_ERROR CPU AXI/SCU response delivery cycles=%0d",cycles);$finish;end
    if(cycles>4000000) $fatal(1,"Board CPU watchdog");
  end
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(262144),.IMAGE("fault.hex")) memory (
    .clock(clk),
    .reset(reset),
    .aw_bits_id(ddr_awid),
    .aw_bits_addr(ddr_awaddr),
    .aw_bits_len(ddr_awlen),
    .aw_bits_size(ddr_awsize),
    .aw_bits_burst(ddr_awburst),
    .aw_valid(ddr_awvalid),
    .aw_ready(ddr_awready),
    .w_bits_data(ddr_wdata),
    .w_bits_strb(ddr_wstrb),
    .w_bits_last(ddr_wlast),
    .w_valid(ddr_wvalid),
    .w_ready(ddr_wready),
    .b_bits_id(ddr_bid),
    .b_bits_resp(ddr_bresp),
    .b_valid(ddr_bvalid),
    .b_ready(ddr_bready),
    .ar_bits_id(ddr_arid),
    .ar_bits_addr(ddr_araddr),
    .ar_bits_len(ddr_arlen),
    .ar_bits_size(ddr_arsize),
    .ar_bits_burst(ddr_arburst),
    .ar_valid(ddr_arvalid),
    .ar_ready(ddr_arready),
    .r_bits_id(ddr_rid),
    .r_bits_data(ddr_rdata),
    .r_bits_resp(ddr_rresp),
    .r_bits_last(ddr_rlast),
    .r_valid(ddr_rvalid),
    .r_ready(ddr_rready)
  );

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

endmodule
