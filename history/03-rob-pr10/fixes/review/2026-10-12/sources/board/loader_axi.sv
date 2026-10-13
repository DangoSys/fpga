// Convert a held loader byte request into a completed AXI transaction.
// The loader advances only after B/R. A RELEASE cycle prevents resubmission
// while its synchronous state machine consumes the acknowledgement.
module loader_axi (
  input wire clk, reset, load_en,
  input wire [27:0] load_addr,
  input wire [127:0] load_data, input wire [15:0] load_mask,
  output reg load_valid, load_error, output reg [127:0] load_result,
  output wire [27:0] awaddr, araddr,
  output wire awvalid, wvalid, arvalid, bready, rready,
  input wire awready, wready, arready, bvalid, rvalid,
  output wire [127:0] wdata, output wire [15:0] wstrb,
  input wire [1:0] bresp, rresp, input wire [127:0] rdata
);
  localparam IDLE=0, SEND_W=1, WAIT_B=2, SEND_R=3, WAIT_R=4, RELEASE=5;
  reg [2:0] state;
  reg [27:0] addr;
  reg [127:0] data;
  reg [15:0] mask;
  reg sent_aw, sent_w;
  assign awaddr=addr;assign araddr=addr;
  assign wdata=data;assign wstrb=mask;
  assign awvalid=!reset && state==SEND_W && !sent_aw;
  assign wvalid=!reset && state==SEND_W && !sent_w;
  assign arvalid=!reset && state==SEND_R;
  assign bready=!reset && state==WAIT_B;
  assign rready=!reset && state==WAIT_R;
  always @(posedge clk) begin
    load_valid<=0;
    if(reset) begin
      state<=IDLE;addr<=0;data<=0;mask<=0;sent_aw<=0;sent_w<=0;
      load_valid<=0;load_error<=0;load_result<=0;
    end else case(state)
      IDLE:if(load_en) begin
        addr<={load_addr[27:4],4'd0};data<=load_data;mask<=load_mask;
        sent_aw<=0;sent_w<=0;load_error<=0;
        state<=|load_mask ? SEND_W : SEND_R;
      end
      SEND_W:begin
        if(awvalid && awready) sent_aw<=1;
        if(wvalid && wready) sent_w<=1;
        if((sent_aw || awready) && (sent_w || wready)) state<=WAIT_B;
      end
      WAIT_B:if(bvalid) begin load_valid<=1;load_error<=bresp!=0;state<=RELEASE;end
      SEND_R:if(arready) state<=WAIT_R;
      WAIT_R:if(rvalid) begin
        load_valid<=1;load_error<=rresp!=0;load_result<=rdata;state<=RELEASE;
      end
      RELEASE:state<=IDLE;
      default:state<=IDLE;
    endcase
  end
endmodule
