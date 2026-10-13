// Serialize each INCR/FIXED AXI beat into an aligned 128-bit MIG transaction.
// Lane positions/strobes and IDs are preserved. Narrow reads may overfetch DDR
// bytes but never MMIO. One read and one write burst can progress independently.
module axi_fullwidth (
  input wire clk, reset,
  input wire [3:0] s_awid, s_arid,
  input wire [31:0] s_awaddr, s_araddr,
  input wire [7:0] s_awlen, s_arlen,
  input wire [2:0] s_awsize, s_arsize,
  input wire [1:0] s_awburst, s_arburst,
  input wire s_awvalid, s_arvalid, s_wvalid, s_wlast, s_bready, s_rready,
  output wire s_awready, s_arready, s_wready,
  input wire [127:0] s_wdata, input wire [15:0] s_wstrb,
  output reg [3:0] s_bid, s_rid,
  output reg [1:0] s_bresp, s_rresp,
  output reg s_bvalid, s_rvalid, s_rlast, output reg [127:0] s_rdata,
  output wire [3:0] m_awid, m_arid,
  output wire [27:0] m_awaddr, m_araddr,
  output wire [7:0] m_awlen, m_arlen,
  output wire [2:0] m_awsize, m_arsize,
  output wire [1:0] m_awburst, m_arburst,
  output wire m_awvalid, m_arvalid, m_wvalid, m_wlast, m_bready, m_rready,
  input wire m_awready, m_arready, m_wready,
  output wire [127:0] m_wdata, output wire [15:0] m_wstrb,
  input wire [3:0] m_bid, m_rid,
  input wire [1:0] m_bresp, m_rresp,
  input wire m_bvalid, m_rvalid, m_rlast, input wire [127:0] m_rdata
);
  localparam W_IDLE=0, W_DATA=1, W_SEND=2, W_RESP=3;
  localparam R_IDLE=0, R_SEND=1, R_RESP=2, R_RETURN=3;
  reg [1:0] ws, rs;
  reg [31:0] wa, ra;
  reg [7:0] wl, rl;
  reg [2:0] wz, rz;
  reg wi, ri, wbad, rbad, aw_sent, w_sent;
  reg [127:0] wd;
  reg [15:0] wm;
  wire [32:0] wend = {1'b0,s_awaddr} + ({25'd0,s_awlen} << s_awsize);
  wire [32:0] rend = {1'b0,s_araddr} + ({25'd0,s_arlen} << s_arsize);
  wire wlegal = s_awaddr[31:28]==4'h8 && s_awsize<=4 && s_awburst<=1 &&
    (s_awaddr & ((32'd1<<s_awsize)-1))==0 &&
    (s_awburst==0 || (wend[32:28]==5'h08 && wend[31:12]==s_awaddr[31:12]));
  wire rlegal = s_araddr[31:28]==4'h8 && s_arsize<=4 && s_arburst<=1 &&
    (s_araddr & ((32'd1<<s_arsize)-1))==0 &&
    (s_arburst==0 || (rend[32:28]==5'h08 && rend[31:12]==s_araddr[31:12]));
  assign s_awready = !reset && ws==W_IDLE && !s_bvalid;
  assign s_wready = !reset && ws==W_DATA;
  assign s_arready = !reset && rs==R_IDLE;
  assign m_awid=s_bid; assign m_arid=s_rid;
  assign m_awaddr={wa[27:4],4'd0}; assign m_araddr={ra[27:4],4'd0};
  assign m_awlen=0; assign m_arlen=0;
  assign m_awsize=4; assign m_arsize=4;
  assign m_awburst=1; assign m_arburst=1;
  assign m_awvalid=!reset && ws==W_SEND && !aw_sent;
  assign m_wvalid=!reset && ws==W_SEND && !w_sent;
  assign m_wdata=wd; assign m_wstrb=wm; assign m_wlast=1;
  assign m_bready=!reset && ws==W_RESP;
  assign m_arvalid=!reset && rs==R_SEND;
  assign m_rready=!reset && rs==R_RESP;
  always @(posedge clk) begin
    if(reset) begin
      ws<=W_IDLE;rs<=R_IDLE;wa<=0;ra<=0;wl<=0;rl<=0;wz<=0;rz<=0;
      wi<=0;ri<=0;wbad<=0;rbad<=0;aw_sent<=0;w_sent<=0;wd<=0;wm<=0;
      s_bid<=0;s_rid<=0;s_bresp<=0;s_rresp<=0;s_bvalid<=0;s_rvalid<=0;s_rlast<=0;s_rdata<=0;
    end else begin
      if(s_bvalid && s_bready) s_bvalid<=0;
      case(ws)
        W_IDLE:if(s_awvalid && s_awready) begin
          wa<=s_awaddr;wl<=s_awlen;wz<=s_awsize;wi<=s_awburst==1;
          s_bid<=s_awid;s_bresp<=0;wbad<=!wlegal;ws<=W_DATA;
        end
        W_DATA:if(s_wvalid && s_wready) begin
          wd<=s_wdata;wm<=s_wstrb;aw_sent<=0;w_sent<=0;
          if(s_wlast!=(wl==0)) s_bresp<=2;
          if(wbad) begin
            s_bresp<=2;
            if(wl==0) begin s_bvalid<=1;ws<=W_IDLE;end
            else wl<=wl-1'b1;
          end else ws<=W_SEND;
        end
        W_SEND:begin
          if(m_awvalid && m_awready) aw_sent<=1;
          if(m_wvalid && m_wready) w_sent<=1;
          if((aw_sent || m_awready) && (w_sent || m_wready)) ws<=W_RESP;
        end
        W_RESP:if(m_bvalid) begin
          if(m_bresp!=0 || m_bid!=s_bid) s_bresp<=2;
          if(wl==0) begin s_bvalid<=1;ws<=W_IDLE;end
          else begin wl<=wl-1'b1;if(wi) wa<=wa+(32'd1<<wz);ws<=W_DATA;end
        end
      endcase
      case(rs)
        R_IDLE:if(s_arvalid && s_arready) begin
          ra<=s_araddr;rl<=s_arlen;rz<=s_arsize;ri<=s_arburst==1;
          s_rid<=s_arid;rbad<=!rlegal;s_rlast<=s_arlen==0;
          if(!rlegal) begin s_rdata<=0;s_rresp<=2;s_rvalid<=1;rs<=R_RETURN;end
          else rs<=R_SEND;
        end
        R_SEND:if(m_arready) rs<=R_RESP;
        R_RESP:if(m_rvalid) begin
          s_rdata<=m_rdata;s_rresp<=m_rid!=s_rid || !m_rlast ? 2'b10 : m_rresp;
          s_rvalid<=1;rs<=R_RETURN;
        end
        R_RETURN:if(s_rvalid && s_rready) begin
          s_rvalid<=0;
          if(rl==0) rs<=R_IDLE;
          else begin
            rl<=rl-1'b1;s_rlast<=rl==1;if(ri) ra<=ra+(32'd1<<rz);
            if(rbad) s_rvalid<=1;else rs<=R_SEND;
          end
        end
      endcase
    end
  end
endmodule
