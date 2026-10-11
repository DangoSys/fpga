// Generated wiring; source CPU/accelerator RTL is byte-identical.
module toy_a7_platform #(parameter UART_DIVISOR=25) (
  input wire clk, reset, uart_rx_in,
  output wire uart_tx_out, cpu_run, exited, loader_error,
  output wire [31:0] exit_code,
  output wire [3:0] ddr_awid,
  output wire [27:0] ddr_awaddr,
  output wire [7:0] ddr_awlen,
  output wire [2:0] ddr_awsize,
  output wire [1:0] ddr_awburst,
  output wire ddr_awvalid,
  input wire ddr_awready,
  output wire [127:0] ddr_wdata,
  output wire [15:0] ddr_wstrb,
  output wire ddr_wlast,
  output wire ddr_wvalid,
  input wire ddr_wready,
  input wire [3:0] ddr_bid,
  input wire [1:0] ddr_bresp,
  input wire ddr_bvalid,
  output wire ddr_bready,
  output wire [3:0] ddr_arid,
  output wire [27:0] ddr_araddr,
  output wire [7:0] ddr_arlen,
  output wire [2:0] ddr_arsize,
  output wire [1:0] ddr_arburst,
  output wire ddr_arvalid,
  input wire ddr_arready,
  input wire [3:0] ddr_rid,
  input wire [127:0] ddr_rdata,
  input wire [1:0] ddr_rresp,
  input wire ddr_rlast,
  input wire ddr_rvalid,
  output wire ddr_rready
);
  wire cpu_reset=reset || !cpu_run;
  wire irq;
  wire rx_valid, rx_error, tx_ready, loader_tx_valid, mmio_tx_valid;
  wire [7:0] rx_data, loader_tx_data, mmio_tx_data;
  wire load_en, load_valid, load_error; wire [27:0] load_addr;
  wire [127:0] load_data, load_result; wire [15:0] load_mask;
  uart_rx #(.DIVISOR(UART_DIVISOR)) receiver (.clk(clk),.reset(reset),.rx(uart_rx_in),
    .valid(rx_valid),.data(rx_data),.frame_error(rx_error));
  uart_tx #(.DIVISOR(UART_DIVISOR)) transmitter (.clk(clk),.reset(reset),
    .valid(cpu_run ? mmio_tx_valid : loader_tx_valid),.data(cpu_run ? mmio_tx_data : loader_tx_data),
    .ready(tx_ready),.tx(uart_tx_out));
  ddr_uart_loader loader (.clk(clk),.reset(reset),.rx_valid(rx_valid && !cpu_run),.rx_data(rx_data),
    .rx_error(rx_error),.tx_valid(loader_tx_valid),.tx_data(loader_tx_data),.tx_ready(tx_ready),
    .cpu_run(cpu_run),.error_seen(loader_error),.load_en(load_en),.load_addr(load_addr),
    .load_data(load_data),.load_mask(load_mask),.load_valid(load_valid),.load_error(load_error),.load_result(load_result));
  wire memory_aw_ready;
  wire memory_aw_valid;
  wire [3:0]   memory_aw_bits_id;
  wire [31:0]  memory_aw_bits_addr;
  wire [7:0]   memory_aw_bits_len;
  wire [2:0]   memory_aw_bits_size;
  wire [1:0]   memory_aw_bits_burst;
  wire memory_aw_bits_lock;
  wire [3:0]   memory_aw_bits_cache;
  wire [2:0]   memory_aw_bits_prot;
  wire [3:0]   memory_aw_bits_qos;
  wire memory_w_ready;
  wire memory_w_valid;
  wire [127:0] memory_w_bits_data;
  wire [15:0]  memory_w_bits_strb;
  wire memory_w_bits_last;
  wire memory_b_ready;
  wire memory_b_valid;
  wire [3:0]   memory_b_bits_id;
  wire [1:0]   memory_b_bits_resp;
  wire memory_ar_ready;
  wire memory_ar_valid;
  wire [3:0]   memory_ar_bits_id;
  wire [31:0]  memory_ar_bits_addr;
  wire [7:0]   memory_ar_bits_len;
  wire [2:0]   memory_ar_bits_size;
  wire [1:0]   memory_ar_bits_burst;
  wire memory_ar_bits_lock;
  wire [3:0]   memory_ar_bits_cache;
  wire [2:0]   memory_ar_bits_prot;
  wire [3:0]   memory_ar_bits_qos;
  wire memory_r_ready;
  wire memory_r_valid;
  wire [3:0]   memory_r_bits_id;
  wire [127:0] memory_r_bits_data;
  wire [1:0]   memory_r_bits_resp;
  wire memory_r_bits_last;
  wire peripherals_aw_ready;
  wire peripherals_aw_valid;
  wire [1:0]   peripherals_aw_bits_id;
  wire [30:0]  peripherals_aw_bits_addr;
  wire [7:0]   peripherals_aw_bits_len;
  wire [2:0]   peripherals_aw_bits_size;
  wire [1:0]   peripherals_aw_bits_burst;
  wire peripherals_aw_bits_lock;
  wire [3:0]   peripherals_aw_bits_cache;
  wire [2:0]   peripherals_aw_bits_prot;
  wire [3:0]   peripherals_aw_bits_qos;
  wire peripherals_w_ready;
  wire peripherals_w_valid;
  wire [63:0]  peripherals_w_bits_data;
  wire [7:0]   peripherals_w_bits_strb;
  wire peripherals_w_bits_last;
  wire peripherals_b_ready;
  wire peripherals_b_valid;
  wire [1:0]   peripherals_b_bits_id;
  wire [1:0]   peripherals_b_bits_resp;
  wire peripherals_ar_ready;
  wire peripherals_ar_valid;
  wire [1:0]   peripherals_ar_bits_id;
  wire [30:0]  peripherals_ar_bits_addr;
  wire [7:0]   peripherals_ar_bits_len;
  wire [2:0]   peripherals_ar_bits_size;
  wire [1:0]   peripherals_ar_bits_burst;
  wire peripherals_ar_bits_lock;
  wire [3:0]   peripherals_ar_bits_cache;
  wire [2:0]   peripherals_ar_bits_prot;
  wire [3:0]   peripherals_ar_bits_qos;
  wire peripherals_r_ready;
  wire peripherals_r_valid;
  wire [1:0]   peripherals_r_bits_id;
  wire [63:0]  peripherals_r_bits_data;
  wire [1:0]   peripherals_r_bits_resp;
  wire peripherals_r_bits_last;
  ToyLinuxChip chip (
    .clock(clk),
    .reset(cpu_reset),
    .interrupt(irq),
    .memory_aw_ready(memory_aw_ready),
    .memory_aw_valid(memory_aw_valid),
    .memory_aw_bits_id(memory_aw_bits_id),
    .memory_aw_bits_addr(memory_aw_bits_addr),
    .memory_aw_bits_len(memory_aw_bits_len),
    .memory_aw_bits_size(memory_aw_bits_size),
    .memory_aw_bits_burst(memory_aw_bits_burst),
    .memory_aw_bits_lock(memory_aw_bits_lock),
    .memory_aw_bits_cache(memory_aw_bits_cache),
    .memory_aw_bits_prot(memory_aw_bits_prot),
    .memory_aw_bits_qos(memory_aw_bits_qos),
    .memory_w_ready(memory_w_ready),
    .memory_w_valid(memory_w_valid),
    .memory_w_bits_data(memory_w_bits_data),
    .memory_w_bits_strb(memory_w_bits_strb),
    .memory_w_bits_last(memory_w_bits_last),
    .memory_b_ready(memory_b_ready),
    .memory_b_valid(memory_b_valid),
    .memory_b_bits_id(memory_b_bits_id),
    .memory_b_bits_resp(memory_b_bits_resp),
    .memory_ar_ready(memory_ar_ready),
    .memory_ar_valid(memory_ar_valid),
    .memory_ar_bits_id(memory_ar_bits_id),
    .memory_ar_bits_addr(memory_ar_bits_addr),
    .memory_ar_bits_len(memory_ar_bits_len),
    .memory_ar_bits_size(memory_ar_bits_size),
    .memory_ar_bits_burst(memory_ar_bits_burst),
    .memory_ar_bits_lock(memory_ar_bits_lock),
    .memory_ar_bits_cache(memory_ar_bits_cache),
    .memory_ar_bits_prot(memory_ar_bits_prot),
    .memory_ar_bits_qos(memory_ar_bits_qos),
    .memory_r_ready(memory_r_ready),
    .memory_r_valid(memory_r_valid),
    .memory_r_bits_id(memory_r_bits_id),
    .memory_r_bits_data(memory_r_bits_data),
    .memory_r_bits_resp(memory_r_bits_resp),
    .memory_r_bits_last(memory_r_bits_last),
    .peripherals_aw_ready(peripherals_aw_ready),
    .peripherals_aw_valid(peripherals_aw_valid),
    .peripherals_aw_bits_id(peripherals_aw_bits_id),
    .peripherals_aw_bits_addr(peripherals_aw_bits_addr),
    .peripherals_aw_bits_len(peripherals_aw_bits_len),
    .peripherals_aw_bits_size(peripherals_aw_bits_size),
    .peripherals_aw_bits_burst(peripherals_aw_bits_burst),
    .peripherals_aw_bits_lock(peripherals_aw_bits_lock),
    .peripherals_aw_bits_cache(peripherals_aw_bits_cache),
    .peripherals_aw_bits_prot(peripherals_aw_bits_prot),
    .peripherals_aw_bits_qos(peripherals_aw_bits_qos),
    .peripherals_w_ready(peripherals_w_ready),
    .peripherals_w_valid(peripherals_w_valid),
    .peripherals_w_bits_data(peripherals_w_bits_data),
    .peripherals_w_bits_strb(peripherals_w_bits_strb),
    .peripherals_w_bits_last(peripherals_w_bits_last),
    .peripherals_b_ready(peripherals_b_ready),
    .peripherals_b_valid(peripherals_b_valid),
    .peripherals_b_bits_id(peripherals_b_bits_id),
    .peripherals_b_bits_resp(peripherals_b_bits_resp),
    .peripherals_ar_ready(peripherals_ar_ready),
    .peripherals_ar_valid(peripherals_ar_valid),
    .peripherals_ar_bits_id(peripherals_ar_bits_id),
    .peripherals_ar_bits_addr(peripherals_ar_bits_addr),
    .peripherals_ar_bits_len(peripherals_ar_bits_len),
    .peripherals_ar_bits_size(peripherals_ar_bits_size),
    .peripherals_ar_bits_burst(peripherals_ar_bits_burst),
    .peripherals_ar_bits_lock(peripherals_ar_bits_lock),
    .peripherals_ar_bits_cache(peripherals_ar_bits_cache),
    .peripherals_ar_bits_prot(peripherals_ar_bits_prot),
    .peripherals_ar_bits_qos(peripherals_ar_bits_qos),
    .peripherals_r_ready(peripherals_r_ready),
    .peripherals_r_valid(peripherals_r_valid),
    .peripherals_r_bits_id(peripherals_r_bits_id),
    .peripherals_r_bits_data(peripherals_r_bits_data),
    .peripherals_r_bits_resp(peripherals_r_bits_resp),
    .peripherals_r_bits_last(peripherals_r_bits_last)
  );
  wire [3:0] c_awid;
  wire [27:0] c_awaddr;
  wire [7:0] c_awlen;
  wire [2:0] c_awsize;
  wire [1:0] c_awburst;
  wire c_awvalid;
  wire c_awready;
  wire [127:0] c_wdata;
  wire [15:0] c_wstrb;
  wire c_wlast;
  wire c_wvalid;
  wire c_wready;
  wire [3:0] c_bid;
  wire [1:0] c_bresp;
  wire c_bvalid;
  wire c_bready;
  wire [3:0] c_arid;
  wire [27:0] c_araddr;
  wire [7:0] c_arlen;
  wire [2:0] c_arsize;
  wire [1:0] c_arburst;
  wire c_arvalid;
  wire c_arready;
  wire [3:0] c_rid;
  wire [127:0] c_rdata;
  wire [1:0] c_rresp;
  wire c_rlast;
  wire c_rvalid;
  wire c_rready;
  wire [3:0] l_awid;
  wire [27:0] l_awaddr;
  wire [7:0] l_awlen;
  wire [2:0] l_awsize;
  wire [1:0] l_awburst;
  wire l_awvalid;
  wire l_awready;
  wire [127:0] l_wdata;
  wire [15:0] l_wstrb;
  wire l_wlast;
  wire l_wvalid;
  wire l_wready;
  wire [3:0] l_bid;
  wire [1:0] l_bresp;
  wire l_bvalid;
  wire l_bready;
  wire [3:0] l_arid;
  wire [27:0] l_araddr;
  wire [7:0] l_arlen;
  wire [2:0] l_arsize;
  wire [1:0] l_arburst;
  wire l_arvalid;
  wire l_arready;
  wire [3:0] l_rid;
  wire [127:0] l_rdata;
  wire [1:0] l_rresp;
  wire l_rlast;
  wire l_rvalid;
  wire l_rready;
  axi_fullwidth normalizer (
    .clk(clk),
    .reset(reset),
    .s_awid(memory_aw_bits_id),
    .m_awid(c_awid),
    .s_awaddr(memory_aw_bits_addr),
    .m_awaddr(c_awaddr),
    .s_awlen(memory_aw_bits_len),
    .m_awlen(c_awlen),
    .s_awsize(memory_aw_bits_size),
    .m_awsize(c_awsize),
    .s_awburst(memory_aw_bits_burst),
    .m_awburst(c_awburst),
    .s_awvalid(memory_aw_valid),
    .m_awvalid(c_awvalid),
    .s_awready(memory_aw_ready),
    .m_awready(c_awready),
    .s_wdata(memory_w_bits_data),
    .m_wdata(c_wdata),
    .s_wstrb(memory_w_bits_strb),
    .m_wstrb(c_wstrb),
    .s_wlast(memory_w_bits_last),
    .m_wlast(c_wlast),
    .s_wvalid(memory_w_valid),
    .m_wvalid(c_wvalid),
    .s_wready(memory_w_ready),
    .m_wready(c_wready),
    .s_bid(memory_b_bits_id),
    .m_bid(c_bid),
    .s_bresp(memory_b_bits_resp),
    .m_bresp(c_bresp),
    .s_bvalid(memory_b_valid),
    .m_bvalid(c_bvalid),
    .s_bready(memory_b_ready),
    .m_bready(c_bready),
    .s_arid(memory_ar_bits_id),
    .m_arid(c_arid),
    .s_araddr(memory_ar_bits_addr),
    .m_araddr(c_araddr),
    .s_arlen(memory_ar_bits_len),
    .m_arlen(c_arlen),
    .s_arsize(memory_ar_bits_size),
    .m_arsize(c_arsize),
    .s_arburst(memory_ar_bits_burst),
    .m_arburst(c_arburst),
    .s_arvalid(memory_ar_valid),
    .m_arvalid(c_arvalid),
    .s_arready(memory_ar_ready),
    .m_arready(c_arready),
    .s_rid(memory_r_bits_id),
    .m_rid(c_rid),
    .s_rdata(memory_r_bits_data),
    .m_rdata(c_rdata),
    .s_rresp(memory_r_bits_resp),
    .m_rresp(c_rresp),
    .s_rlast(memory_r_bits_last),
    .m_rlast(c_rlast),
    .s_rvalid(memory_r_valid),
    .m_rvalid(c_rvalid),
    .s_rready(memory_r_ready),
    .m_rready(c_rready)
  );
  loader_axi load_bridge (
    .clk(clk),
    .reset(reset),
    .load_en(load_en),
    .load_addr(load_addr),
    .load_data(load_data),
    .load_mask(load_mask),
    .load_valid(load_valid),
    .load_error(load_error),
    .load_result(load_result),
    .awaddr(l_awaddr),
    .araddr(l_araddr),
    .awvalid(l_awvalid),
    .wvalid(l_wvalid),
    .arvalid(l_arvalid),
    .bready(l_bready),
    .rready(l_rready),
    .awready(l_awready),
    .wready(l_wready),
    .arready(l_arready),
    .bvalid(l_bvalid),
    .rvalid(l_rvalid),
    .wdata(l_wdata),
    .wstrb(l_wstrb),
    .bresp(l_bresp),
    .rresp(l_rresp),
    .rdata(l_rdata)
  );
  assign l_awid=0;
  assign l_arid=0;
  assign l_awlen=0;
  assign l_arlen=0;
  assign l_awsize=4;
  assign l_arsize=4;
  assign l_awburst=1;
  assign l_arburst=1;
  assign l_wlast=1;
  assign ddr_awid=cpu_run ? c_awid : l_awid;
  assign ddr_awaddr=cpu_run ? c_awaddr : l_awaddr;
  assign ddr_awlen=cpu_run ? c_awlen : l_awlen;
  assign ddr_awsize=cpu_run ? c_awsize : l_awsize;
  assign ddr_awburst=cpu_run ? c_awburst : l_awburst;
  assign ddr_awvalid=cpu_run ? c_awvalid : l_awvalid;
  assign c_awready=ddr_awready && cpu_run;
  assign l_awready=ddr_awready && !cpu_run;
  assign ddr_wdata=cpu_run ? c_wdata : l_wdata;
  assign ddr_wstrb=cpu_run ? c_wstrb : l_wstrb;
  assign ddr_wlast=cpu_run ? c_wlast : l_wlast;
  assign ddr_wvalid=cpu_run ? c_wvalid : l_wvalid;
  assign c_wready=ddr_wready && cpu_run;
  assign l_wready=ddr_wready && !cpu_run;
  assign c_bid=ddr_bid;
  assign l_bid=ddr_bid;
  assign c_bresp=ddr_bresp;
  assign l_bresp=ddr_bresp;
  assign c_bvalid=ddr_bvalid && cpu_run;
  assign l_bvalid=ddr_bvalid && !cpu_run;
  assign ddr_bready=cpu_run ? c_bready : l_bready;
  assign ddr_arid=cpu_run ? c_arid : l_arid;
  assign ddr_araddr=cpu_run ? c_araddr : l_araddr;
  assign ddr_arlen=cpu_run ? c_arlen : l_arlen;
  assign ddr_arsize=cpu_run ? c_arsize : l_arsize;
  assign ddr_arburst=cpu_run ? c_arburst : l_arburst;
  assign ddr_arvalid=cpu_run ? c_arvalid : l_arvalid;
  assign c_arready=ddr_arready && cpu_run;
  assign l_arready=ddr_arready && !cpu_run;
  assign c_rid=ddr_rid;
  assign l_rid=ddr_rid;
  assign c_rdata=ddr_rdata;
  assign l_rdata=ddr_rdata;
  assign c_rresp=ddr_rresp;
  assign l_rresp=ddr_rresp;
  assign c_rlast=ddr_rlast;
  assign l_rlast=ddr_rlast;
  assign c_rvalid=ddr_rvalid && cpu_run;
  assign l_rvalid=ddr_rvalid && !cpu_run;
  assign ddr_rready=cpu_run ? c_rready : l_rready;
  wire [1:0] scu_bresp;
  assign peripherals_b_bits_resp=|scu_bresp;
  axi_scu peripherals (
    .clk(clk),
    .reset(cpu_reset),
    .awid(peripherals_aw_bits_id),
    .awaddr(peripherals_aw_bits_addr),
    .awlen(peripherals_aw_bits_len),
    .awsize(peripherals_aw_bits_size),
    .awburst(peripherals_aw_bits_burst),
    .awvalid(peripherals_aw_valid),
    .awready(peripherals_aw_ready),
    .wdata(peripherals_w_bits_data),
    .wstrb(peripherals_w_bits_strb),
    .wlast(peripherals_w_bits_last),
    .wvalid(peripherals_w_valid),
    .wready(peripherals_w_ready),
    .bid(peripherals_b_bits_id),
    .bresp(scu_bresp),
    .bvalid(peripherals_b_valid),
    .bready(peripherals_b_ready),
    .arid(peripherals_ar_bits_id),
    .araddr(peripherals_ar_bits_addr),
    .arlen(peripherals_ar_bits_len),
    .arsize(peripherals_ar_bits_size),
    .arburst(peripherals_ar_bits_burst),
    .arvalid(peripherals_ar_valid),
    .arready(peripherals_ar_ready),
    .rid(peripherals_r_bits_id),
    .rdata(peripherals_r_bits_data),
    .rresp(peripherals_r_bits_resp),
    .rlast(peripherals_r_bits_last),
    .rvalid(peripherals_r_valid),
    .rready(peripherals_r_ready),
    .rx_valid(rx_valid && cpu_run),
    .rx_data(rx_data),
    .rx_error(rx_error),
    .tx_valid(mmio_tx_valid),
    .tx_data(mmio_tx_data),
    .tx_ready(tx_ready),
    .exited(exited),
    .exit_code(exit_code),
    .interrupt(irq)
  );
endmodule
