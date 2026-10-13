`timescale 1ns/1ps
module tb_board_uart_boot;
  reg clk=0;always #20 clk=~clk;
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
    repeat(10) @(negedge clk); reset=0;end
  integer cycles=0;
  always @(posedge clk) if(!reset) begin
    cycles<=cycles+1;
    if(platform.memory_aw_valid && platform.memory_aw_bits_lock) $fatal(1,"Unexpected AXI exclusive write");
    if(platform.memory_ar_valid && platform.memory_ar_bits_lock) $fatal(1,"Unexpected AXI exclusive read");
    if(ddr_awvalid && ddr_awready && (ddr_awsize!=4 || ddr_awlen!=0)) $fatal(1,"Narrow DDR write");
    if(ddr_arvalid && ddr_arready && (ddr_arsize!=4 || ddr_arlen!=0)) $fatal(1,"Narrow DDR read");
    if(exited && (exit_code & 32'hffff0000)==32'hbad00000) $fatal(1,"CPU oracle failed stage=%h",exit_code);
    if(exited && exit_code==32'h600d600d) begin
      $display("PASS CPU Sv39/FPU/AMO/cache/interrupt through board AXI/SCU cycles=%0d",cycles);$finish;end
    if(cycles>120000000) $fatal(1,"Board CPU watchdog");
  end
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(262144),.IMAGE("")) memory (
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
  localparam PROGRAM_BYTES=110592;

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

endmodule
