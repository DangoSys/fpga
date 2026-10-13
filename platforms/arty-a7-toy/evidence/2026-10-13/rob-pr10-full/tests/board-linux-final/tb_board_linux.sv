`timescale 1ns/1ps
module tb_board_linux;
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
    repeat(10) @(negedge clk); force platform.loader.cpu_run=1;reset=0;end
  integer cycles=0;
  always @(posedge clk) if(!reset) begin
    cycles<=cycles+1;
    if(platform.memory_aw_valid && platform.memory_aw_bits_lock) $fatal(1,"Unexpected AXI exclusive write");
    if(platform.memory_ar_valid && platform.memory_ar_bits_lock) $fatal(1,"Unexpected AXI exclusive read");
    if(ddr_awvalid && ddr_awready && (ddr_awsize!=4 || ddr_awlen!=0)) $fatal(1,"Narrow DDR write");
    if(ddr_arvalid && ddr_arready && (ddr_arsize!=4 || ddr_arlen!=0)) $fatal(1,"Narrow DDR read");
    if(cycles>500000000) $fatal(1,"Linux cycle watchdog");
  end
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(268435456),.IMAGE("payload.hex")) memory (
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

  reg [255:0] tail=0;
  reg init_seen=0,prompt_seen=0;
  integer characters=0;
  always @(posedge clk) if(!reset && platform.mmio_tx_valid && platform.tx_ready && cpu_run) begin
    tail={tail[247:0],platform.mmio_tx_data};characters=characters+1;
    $write("%c",platform.mmio_tx_data);$fflush();
    if(tail[95:0]=="init process") init_seen=1;
    if(init_seen && tail[15:0]==16'h2320) prompt_seen=1;
    if(tail[183:0]=="PASS LINUX_SYSTEM_CHECK") begin
      $display("\nPASS BOARD_LINUX_USERSPACE cycles=%0d characters=%0d",cycles,characters);$finish;
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
    $display("\nSIM_SHELL_PROMPT cycles=%0d",cycles);$fflush();
    send_byte("/");send_byte("r");send_byte("o");send_byte("o");send_byte("t");send_byte("/");
    send_byte("l");send_byte("i");send_byte("n");send_byte("u");send_byte("x");send_byte("_");
    send_byte("s");send_byte("y");send_byte("s");send_byte("t");send_byte("e");send_byte("m");send_byte("_");
    send_byte("c");send_byte("h");send_byte("e");send_byte("c");send_byte("k");send_byte("-");
    send_byte("l");send_byte("i");send_byte("n");send_byte("u");send_byte("x");send_byte(10);
    $display("\nSIM_COMMAND_SENT cycles=%0d overflow=%0d framing=%0d pending_rx=%0d",cycles,
      platform.peripherals.overflow,platform.peripherals.framing,platform.peripherals.count);$fflush();
    if(platform.peripherals.overflow || platform.peripherals.framing) $fatal(1,"UART input loss");
  end

endmodule
