// Single-hart SCU console used by the pinned Buckyball OpenSBI platform.
// EXIT 0x60000000, TX 0x60020000, RX 0x60020004, STATUS 0x60020005.
// Reads use AXI lane positions; RX pops only after its R response is accepted.
module axi_scu #(parameter FLASH_BOOT=0) (
  input wire clk, reset,
  input wire [1:0] awid, arid,
  input wire [30:0] awaddr, araddr,
  input wire [7:0] awlen, arlen,
  input wire [2:0] awsize, arsize,
  input wire [1:0] awburst, arburst,
  input wire awvalid, arvalid, wvalid, wlast, bready, rready,
  output wire awready, arready, wready,
  input wire [63:0] wdata, input wire [7:0] wstrb,
  output reg [1:0] bid, rid, bresp, rresp,
  output reg bvalid, rvalid, rlast, output reg [63:0] rdata,
  input wire rx_valid, rx_error, input wire [7:0] rx_data,
  output wire tx_valid, output wire [7:0] tx_data, input wire tx_ready,
  output reg exited, output reg [31:0] exit_code, output wire interrupt,
  input wire flash_miso, flash_recovery,
  output wire flash_mosi, flash_sck,
  output reg flash_cs_n
);
  // SBI/HVC is polled. A paste may otherwise overflow a 16-byte FIFO before
  // Linux's next console poll; use RAM-backed 256-byte buffering.
  (* ram_style="distributed" *) reg [7:0] fifo[0:255];
  reg [7:0] rp, wp;
  reg [8:0] count;
  reg overflow, framing, pop_on_read, wa, bad;
  reg [7:0] wr_left, rd_left;
  reg [30:0] wr_addr;
  wire pop=rvalid && rready && pop_on_read;
  wire push=rx_valid && (count<256 || pop);
  wire wr_tx=wr_addr==31'h60020000 && !bad && wstrb[0];
  wire wr_spi=FLASH_BOOT && wr_addr==31'h60020008 && !bad && wstrb[0];
  wire wr_cs=FLASH_BOOT && wr_addr==31'h6002000c && !bad && wstrb[4];
  wire spi_busy;
  wire [7:0] spi_rx;
  generate if(FLASH_BOOT) begin : spi_enabled
    flash_spi_byte flash (.clk(clk),.reset(reset),.start(wvalid && wready && wr_spi),
      .tx_data(wdata[7:0]),.miso(flash_miso),.mosi(flash_mosi),.sck(flash_sck),
      .busy(spi_busy),.rx_data(spi_rx));
  end else begin
    assign spi_busy=0;assign spi_rx=0;assign flash_mosi=0;assign flash_sck=0;
  end endgenerate
  assign awready=!reset && !wa && !bvalid;
  assign arready=!reset && !rvalid;
  assign wready=!reset && wa && (!wr_tx || tx_ready) && (!(wr_spi || wr_cs) || !spi_busy);
  assign tx_valid=!reset && wa && wvalid && wr_tx;
  assign tx_data=wdata[7:0];
  assign interrupt=count!=0;
  always @(posedge clk) begin
    if(reset) begin
      rp<=0;wp<=0;count<=0;overflow<=0;framing<=0;pop_on_read<=0;
      wa<=0;bad<=0;wr_left<=0;rd_left<=0;wr_addr<=0;
      bid<=0;rid<=0;bresp<=0;rresp<=0;bvalid<=0;rvalid<=0;rlast<=0;rdata<=0;
      exited<=0;exit_code<=0;
      flash_cs_n<=1;
    end else begin
      if(bvalid) bvalid<=0;
      if(awvalid && awready) begin
        wa<=1;bid<=awid;wr_addr<=awaddr;wr_left<=awlen;
        bad<=awlen!=0 || awsize>3 || awburst>1 ||
          (awaddr & ((31'd1<<awsize)-1))!=0 ||
          !(awaddr==31'h60000000 || awaddr==31'h60020000 ||
            (FLASH_BOOT && awsize==0 && (awaddr==31'h60020008 || awaddr==31'h6002000c)));
      end
      if(wvalid && wready) begin
        if(wr_cs) flash_cs_n<=wdata[32];
        if(!bad && wr_addr==31'h60000000) begin
          for(integer n=0;n<4;n=n+1) if(wstrb[n]) exit_code[8*n+:8]<=wdata[8*n+:8];
          if(|wstrb[3:0]) exited<=1;
        end
        if(wr_left==0) begin wa<=0;bvalid<=1;bresp<=bad || !wlast ? 2'b10 : 2'b00;end
        else begin wr_left<=wr_left-1'b1;bad<=1;end
      end
      if(rvalid && rready) begin
        pop_on_read<=0;
        if(rd_left==0) rvalid<=0;
        else begin rd_left<=rd_left-1'b1;rlast<=rd_left==1;end
      end
      if(arvalid && arready) begin
        rid<=arid;rvalid<=1;rlast<=arlen==0;rd_left<=arlen;
        rdata<=0;rresp<=0;pop_on_read<=0;
        if(arlen!=0 || arsize>3 || arburst>1 || (araddr & ((31'd1<<arsize)-1))!=0) rresp<=2;
        else if(araddr==31'h60000000) rdata<={31'd0,exited,exit_code};
        else if(araddr==31'h60020004 && arsize==0) begin
          rdata[39:32]<=count!=0 ? fifo[rp] : 8'd0;pop_on_read<=count!=0;
        end else if(araddr==31'h60020005 && arsize==0)
          rdata[47:40]<={5'd0,framing,overflow,count!=0};
        else if(FLASH_BOOT && araddr==31'h60020008 && arsize==0) rdata[7:0]<=spi_rx;
        else if(FLASH_BOOT && araddr==31'h60020009 && arsize==0) rdata[15:8]<={7'd0,spi_busy};
        else if(FLASH_BOOT && araddr==31'h6002000a && arsize==0) rdata[23:16]<={7'd0,!flash_recovery};
        else if(FLASH_BOOT && araddr==31'h6002000c && arsize==0) rdata[39:32]<={7'd0,flash_cs_n};
        else if(araddr==31'h60020000) begin
          if(arsize>=3) rdata[47:40]<={5'd0,framing,overflow,count!=0};
        end else rresp<=2;
      end
      if(push) begin fifo[wp]<=rx_data;wp<=wp+1'b1;end
      if(pop) rp<=rp+1'b1;
      case({push,pop})
        2'b10:count<=count+1'b1;
        2'b01:count<=count-1'b1;
        default:count<=count;
      endcase
      if(rx_valid && !push) overflow<=1;
      if(rx_error) framing<=1;
    end
  end
endmodule
