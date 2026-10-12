module toy_a7_top #(parameter FLASH_BOOT=0) (
  input wire CLK100MHZ, btn0, uart_txd_in, output wire uart_rxd_out, output wire [3:0] led,
  inout wire [15:0] ddr3_dq, inout wire [1:0] ddr3_dqs_n, ddr3_dqs_p,
  output wire [13:0] ddr3_addr, output wire [2:0] ddr3_ba,
  output wire ddr3_ras_n, ddr3_cas_n, ddr3_we_n, ddr3_reset_n,
  output wire [0:0] ddr3_ck_p, ddr3_ck_n, ddr3_cke, ddr3_cs_n, ddr3_odt, output wire [1:0] ddr3_dm,
  input wire sw0, flash_miso,
  output wire flash_mosi, flash_cs_n, flash_wp_n, flash_hold_n
);
  wire clk_in,fb,fb_buf,core_raw,sys_raw,ref_raw,clk,sys_clk,ref_clk,locked;
  IBUF input_clock (.I(CLK100MHZ),.O(clk_in));
  MMCME2_BASE #(.CLKIN1_PERIOD(10.0),.DIVCLK_DIVIDE(1),.CLKFBOUT_MULT_F(10.0),
    .CLKOUT0_DIVIDE_F(40.0),.CLKOUT1_DIVIDE(6),.CLKOUT2_DIVIDE(5)) clock_mmcm (
    .CLKIN1(clk_in),.CLKFBIN(fb_buf),.CLKFBOUT(fb),.CLKOUT0(core_raw),
    .CLKOUT1(sys_raw),.CLKOUT2(ref_raw),.LOCKED(locked),.RST(1'b0),.PWRDWN(1'b0));
  BUFG fb_buffer (.I(fb),.O(fb_buf)); BUFG core_buffer (.I(core_raw),.O(clk));
  BUFG sys_buffer (.I(sys_raw),.O(sys_clk)); BUFG ref_buffer (.I(ref_raw),.O(ref_clk));
  wire ui_clk,ui_rst,mig_locked,calibrated;
  wire flash_sck;
  assign flash_wp_n=1;assign flash_hold_n=1;
  generate if(FLASH_BOOT) begin : flash_clock
    STARTUPE2 startup (.CLK(1'b0),.GSR(1'b0),.GTS(1'b0),.KEYCLEARB(1'b1),.PACK(1'b0),
      .USRCCLKO(flash_sck),.USRCCLKTS(1'b0),.USRDONEO(1'b1),.USRDONETS(1'b1),
      .CFGCLK(),.CFGMCLK(),.EOS(),.PREQ());
  end endgenerate
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg sw_meta=0,sw_sync=0;
  reg flash_recovery=0;
  always @(posedge clk) begin
    sw_meta<=sw0;sw_sync<=sw_meta;
    if(reset) flash_recovery<=sw_sync;
  end
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg [2:0] lock_sync=7;
  always @(posedge clk or negedge locked) if(!locked) lock_sync<=7;else lock_sync<={lock_sync[1:0],1'b0};
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg btn_meta=0,btn_sync=0;
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg btn_ref_meta=0,btn_ref_sync=0;
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg [2:0] mig_resetn_pipe=0;
  always @(posedge ref_clk) begin btn_ref_meta<=btn0;btn_ref_sync<=btn_ref_meta;end
  always @(posedge ref_clk or negedge locked) if(!locked) mig_resetn_pipe<=0;
    else mig_resetn_pipe<={mig_resetn_pipe[1:0],!btn_ref_sync};
  wire mig_resetn=mig_resetn_pipe[2];
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg [1:0] calib_sync=0;
  always @(posedge clk) begin btn_meta<=btn0;btn_sync<=btn_meta;calib_sync<={calib_sync[0],calibrated};end
  reg [17:0] reset_count=0;wire reset=lock_sync[2] || btn_sync || !calib_sync[1] || !(&reset_count);
  always @(posedge clk) if(lock_sync[2] || btn_sync || !calib_sync[1]) reset_count<=0;
    else if(!(&reset_count)) reset_count<=reset_count+1'b1;
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg [2:0] ui_reset_pipe=7;
  always @(posedge ui_clk or posedge ui_rst) if(ui_rst) ui_reset_pipe<=7;
    else ui_reset_pipe<={ui_reset_pipe[1:0],1'b0};
  wire ui_aresetn=~ui_reset_pipe[2];
  wire cpu_run,exited,loader_error;wire [31:0] exit_code;reg [24:0] heartbeat=0;
  always @(posedge clk) if(reset) heartbeat<=0;else heartbeat<=heartbeat+1'b1;
  assign led={heartbeat[24],cpu_run && !reset,loader_error || (exited && exit_code!=0),calib_sync[1]};
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
  wire [3:0] ui_awid;
  wire [27:0] ui_awaddr;
  wire [7:0] ui_awlen;
  wire [2:0] ui_awsize;
  wire [1:0] ui_awburst;
  wire ui_awvalid;
  wire ui_awready;
  wire [127:0] ui_wdata;
  wire [15:0] ui_wstrb;
  wire ui_wlast;
  wire ui_wvalid;
  wire ui_wready;
  wire [3:0] ui_bid;
  wire [1:0] ui_bresp;
  wire ui_bvalid;
  wire ui_bready;
  wire [3:0] ui_arid;
  wire [27:0] ui_araddr;
  wire [7:0] ui_arlen;
  wire [2:0] ui_arsize;
  wire [1:0] ui_arburst;
  wire ui_arvalid;
  wire ui_arready;
  wire [3:0] ui_rid;
  wire [127:0] ui_rdata;
  wire [1:0] ui_rresp;
  wire ui_rlast;
  wire ui_rvalid;
  wire ui_rready;
  toy_a7_platform #(.FLASH_BOOT(FLASH_BOOT)) platform (
    .clk(clk),
    .reset(reset),
    .uart_rx_in(uart_txd_in),
    .uart_tx_out(uart_rxd_out),
    .cpu_run(cpu_run),
    .exited(exited),
    .loader_error(loader_error),
    .exit_code(exit_code),
    .flash_miso(flash_miso),.flash_mosi(flash_mosi),.flash_sck(flash_sck),
    .flash_cs_n(flash_cs_n),.flash_recovery(flash_recovery),
    .ddr_awid(ddr_awid),
    .ddr_awaddr(ddr_awaddr),
    .ddr_awlen(ddr_awlen),
    .ddr_awsize(ddr_awsize),
    .ddr_awburst(ddr_awburst),
    .ddr_awvalid(ddr_awvalid),
    .ddr_awready(ddr_awready),
    .ddr_wdata(ddr_wdata),
    .ddr_wstrb(ddr_wstrb),
    .ddr_wlast(ddr_wlast),
    .ddr_wvalid(ddr_wvalid),
    .ddr_wready(ddr_wready),
    .ddr_bid(ddr_bid),
    .ddr_bresp(ddr_bresp),
    .ddr_bvalid(ddr_bvalid),
    .ddr_bready(ddr_bready),
    .ddr_arid(ddr_arid),
    .ddr_araddr(ddr_araddr),
    .ddr_arlen(ddr_arlen),
    .ddr_arsize(ddr_arsize),
    .ddr_arburst(ddr_arburst),
    .ddr_arvalid(ddr_arvalid),
    .ddr_arready(ddr_arready),
    .ddr_rid(ddr_rid),
    .ddr_rdata(ddr_rdata),
    .ddr_rresp(ddr_rresp),
    .ddr_rlast(ddr_rlast),
    .ddr_rvalid(ddr_rvalid),
    .ddr_rready(ddr_rready)
  );
  toy_axi_cdc memory_cdc (
    .s_axi_aclk(clk),
    .s_axi_aresetn(!reset),
    .m_axi_aclk(ui_clk),
    .m_axi_aresetn(ui_aresetn),
    .s_axi_awid(ddr_awid),
    .s_axi_awaddr(ddr_awaddr),
    .s_axi_awlen(ddr_awlen),
    .s_axi_awsize(ddr_awsize),
    .s_axi_awburst(ddr_awburst),
    .s_axi_awvalid(ddr_awvalid),
    .s_axi_awready(ddr_awready),
    .s_axi_wdata(ddr_wdata),
    .s_axi_wstrb(ddr_wstrb),
    .s_axi_wlast(ddr_wlast),
    .s_axi_wvalid(ddr_wvalid),
    .s_axi_wready(ddr_wready),
    .s_axi_bid(ddr_bid),
    .s_axi_bresp(ddr_bresp),
    .s_axi_bvalid(ddr_bvalid),
    .s_axi_bready(ddr_bready),
    .s_axi_arid(ddr_arid),
    .s_axi_araddr(ddr_araddr),
    .s_axi_arlen(ddr_arlen),
    .s_axi_arsize(ddr_arsize),
    .s_axi_arburst(ddr_arburst),
    .s_axi_arvalid(ddr_arvalid),
    .s_axi_arready(ddr_arready),
    .s_axi_rid(ddr_rid),
    .s_axi_rdata(ddr_rdata),
    .s_axi_rresp(ddr_rresp),
    .s_axi_rlast(ddr_rlast),
    .s_axi_rvalid(ddr_rvalid),
    .s_axi_rready(ddr_rready),
    .s_axi_awlock(1'b0),
    .s_axi_arlock(1'b0),
    .s_axi_awcache(4'b0011),
    .s_axi_arcache(4'b0011),
    .s_axi_awprot(3'd0),
    .s_axi_arprot(3'd0),
    .s_axi_awqos(4'd0),
    .s_axi_arqos(4'd0),
    .s_axi_awregion(4'd0),
    .s_axi_arregion(4'd0),
    .m_axi_awid(ui_awid),
    .m_axi_awaddr(ui_awaddr),
    .m_axi_awlen(ui_awlen),
    .m_axi_awsize(ui_awsize),
    .m_axi_awburst(ui_awburst),
    .m_axi_awvalid(ui_awvalid),
    .m_axi_awready(ui_awready),
    .m_axi_wdata(ui_wdata),
    .m_axi_wstrb(ui_wstrb),
    .m_axi_wlast(ui_wlast),
    .m_axi_wvalid(ui_wvalid),
    .m_axi_wready(ui_wready),
    .m_axi_bid(ui_bid),
    .m_axi_bresp(ui_bresp),
    .m_axi_bvalid(ui_bvalid),
    .m_axi_bready(ui_bready),
    .m_axi_arid(ui_arid),
    .m_axi_araddr(ui_araddr),
    .m_axi_arlen(ui_arlen),
    .m_axi_arsize(ui_arsize),
    .m_axi_arburst(ui_arburst),
    .m_axi_arvalid(ui_arvalid),
    .m_axi_arready(ui_arready),
    .m_axi_rid(ui_rid),
    .m_axi_rdata(ui_rdata),
    .m_axi_rresp(ui_rresp),
    .m_axi_rlast(ui_rlast),
    .m_axi_rvalid(ui_rvalid),
    .m_axi_rready(ui_rready),
    .m_axi_awlock(),
    .m_axi_arlock(),
    .m_axi_awcache(),
    .m_axi_arcache(),
    .m_axi_awprot(),
    .m_axi_arprot(),
    .m_axi_awqos(),
    .m_axi_arqos(),
    .m_axi_awregion(),
    .m_axi_arregion()
  );
  arty_ddr3 ddr_controller (
    .ddr3_dq(ddr3_dq),
    .ddr3_dqs_n(ddr3_dqs_n),
    .ddr3_dqs_p(ddr3_dqs_p),
    .ddr3_addr(ddr3_addr),
    .ddr3_ba(ddr3_ba),
    .ddr3_ras_n(ddr3_ras_n),
    .ddr3_cas_n(ddr3_cas_n),
    .ddr3_we_n(ddr3_we_n),
    .ddr3_reset_n(ddr3_reset_n),
    .ddr3_ck_p(ddr3_ck_p),
    .ddr3_ck_n(ddr3_ck_n),
    .ddr3_cke(ddr3_cke),
    .ddr3_cs_n(ddr3_cs_n),
    .ddr3_dm(ddr3_dm),
    .ddr3_odt(ddr3_odt),
    .sys_clk_i(sys_clk),
    .clk_ref_i(ref_clk),
    .sys_rst(mig_resetn),
    .ui_clk(ui_clk),
    .ui_clk_sync_rst(ui_rst),
    .mmcm_locked(mig_locked),
    .aresetn(ui_aresetn),
    .init_calib_complete(calibrated),
    .device_temp(),
    .app_sr_req(1'b0),
    .app_ref_req(1'b0),
    .app_zq_req(1'b0),
    .app_sr_active(),
    .app_ref_ack(),
    .app_zq_ack(),
    .s_axi_awid(ui_awid),
    .s_axi_awaddr(ui_awaddr),
    .s_axi_awlen(ui_awlen),
    .s_axi_awsize(ui_awsize),
    .s_axi_awburst(ui_awburst),
    .s_axi_awvalid(ui_awvalid),
    .s_axi_awready(ui_awready),
    .s_axi_wdata(ui_wdata),
    .s_axi_wstrb(ui_wstrb),
    .s_axi_wlast(ui_wlast),
    .s_axi_wvalid(ui_wvalid),
    .s_axi_wready(ui_wready),
    .s_axi_bid(ui_bid),
    .s_axi_bresp(ui_bresp),
    .s_axi_bvalid(ui_bvalid),
    .s_axi_bready(ui_bready),
    .s_axi_arid(ui_arid),
    .s_axi_araddr(ui_araddr),
    .s_axi_arlen(ui_arlen),
    .s_axi_arsize(ui_arsize),
    .s_axi_arburst(ui_arburst),
    .s_axi_arvalid(ui_arvalid),
    .s_axi_arready(ui_arready),
    .s_axi_rid(ui_rid),
    .s_axi_rdata(ui_rdata),
    .s_axi_rresp(ui_rresp),
    .s_axi_rlast(ui_rlast),
    .s_axi_rvalid(ui_rvalid),
    .s_axi_rready(ui_rready),
    .s_axi_awlock(1'b0),
    .s_axi_arlock(1'b0),
    .s_axi_awcache(4'b0011),
    .s_axi_arcache(4'b0011),
    .s_axi_awprot(3'd0),
    .s_axi_arprot(3'd0),
    .s_axi_awqos(4'd0),
    .s_axi_arqos(4'd0)
  );
endmodule
