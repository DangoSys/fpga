`timescale 1ns/1ps
module tb_board_cdc;
  reg clk=0;always #20 clk=~clk;
  reg ui_clk=0; initial begin #3; forever #6 ui_clk=~ui_clk; end
  reg reset=1;
  reg [3:0] s_awid=0,s_arid=0;
  reg [31:0] s_awaddr=0,s_araddr=0;
  reg [7:0] s_awlen=0,s_arlen=0;
  reg [2:0] s_awsize=0,s_arsize=0;
  reg [1:0] s_awburst=1,s_arburst=1;
  reg s_awvalid=0,s_arvalid=0,s_wvalid=0,s_wlast=0,s_bready=0,s_rready=0;
  wire s_awready,s_arready,s_wready;
  reg [127:0] s_wdata=0;reg [15:0] s_wstrb=0;
  wire [3:0] s_bid,s_rid;wire [1:0] s_bresp,s_rresp;
  wire s_bvalid,s_rvalid,s_rlast;wire [127:0] s_rdata;
  wire [3:0] m_awid,m_arid;
  wire [27:0] m_awaddr,m_araddr;wire [7:0] m_awlen,m_arlen;
  wire [2:0] m_awsize,m_arsize;wire [1:0] m_awburst,m_arburst;
  wire m_awvalid,m_arvalid,m_wvalid,m_wlast,m_bready,m_rready;
  wire m_awready,m_arready,m_wready;
  wire [127:0] m_wdata;wire [15:0] m_wstrb;
  wire [3:0] m_bid,m_rid;wire [1:0] m_bresp,m_rresp;
  wire m_bvalid,m_rvalid,m_rlast;wire [127:0] m_rdata;
  reg [7:0] expected[0:4095];
  integer beats=0;
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
  toy_axi_cdc memory_cdc (
    .s_axi_aclk(clk),
    .s_axi_aresetn(!reset),
    .m_axi_aclk(ui_clk),
    .m_axi_aresetn(!reset),
    .s_axi_awid(m_awid),
    .s_axi_awaddr(m_awaddr),
    .s_axi_awlen(m_awlen),
    .s_axi_awsize(m_awsize),
    .s_axi_awburst(m_awburst),
    .s_axi_awvalid(m_awvalid),
    .s_axi_awready(m_awready),
    .s_axi_wdata(m_wdata),
    .s_axi_wstrb(m_wstrb),
    .s_axi_wlast(m_wlast),
    .s_axi_wvalid(m_wvalid),
    .s_axi_wready(m_wready),
    .s_axi_bid(m_bid),
    .s_axi_bresp(m_bresp),
    .s_axi_bvalid(m_bvalid),
    .s_axi_bready(m_bready),
    .s_axi_arid(m_arid),
    .s_axi_araddr(m_araddr),
    .s_axi_arlen(m_arlen),
    .s_axi_arsize(m_arsize),
    .s_axi_arburst(m_arburst),
    .s_axi_arvalid(m_arvalid),
    .s_axi_arready(m_arready),
    .s_axi_rid(m_rid),
    .s_axi_rdata(m_rdata),
    .s_axi_rresp(m_rresp),
    .s_axi_rlast(m_rlast),
    .s_axi_rvalid(m_rvalid),
    .s_axi_rready(m_rready),
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
  axi_fullwidth dut(.*);
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(4096)) memory (
    .clock(ui_clk),.reset(reset),
    .aw_ready(ui_awready),.aw_valid(ui_awvalid),.aw_bits_id(ui_awid),.aw_bits_addr(ui_awaddr),
    .aw_bits_len(ui_awlen),.aw_bits_size(ui_awsize),.aw_bits_burst(ui_awburst),
    .w_ready(ui_wready),.w_valid(ui_wvalid),.w_bits_data(ui_wdata),.w_bits_strb(ui_wstrb),.w_bits_last(ui_wlast),
    .b_ready(ui_bready),.b_valid(ui_bvalid),.b_bits_id(ui_bid),.b_bits_resp(ui_bresp),
    .ar_ready(ui_arready),.ar_valid(ui_arvalid),.ar_bits_id(ui_arid),.ar_bits_addr(ui_araddr),
    .ar_bits_len(ui_arlen),.ar_bits_size(ui_arsize),.ar_bits_burst(ui_arburst),
    .r_ready(ui_rready),.r_valid(ui_rvalid),.r_bits_id(ui_rid),.r_bits_data(ui_rdata),.r_bits_resp(ui_rresp),.r_bits_last(ui_rlast));
  always @(posedge clk) begin
    if(m_awvalid && m_awready && (m_awaddr[3:0]!=0 || m_awsize!=4 || m_awlen!=0)) $fatal(1,"MIG narrow write");
    if(m_arvalid && m_arready && (m_araddr[3:0]!=0 || m_arsize!=4 || m_arlen!=0)) $fatal(1,"MIG narrow read");
  end
  task automatic write_burst(input integer address,z,n,id,input bit fixed_addr,input [1:0] response);
    integer a;
    begin
      @(negedge clk);s_awaddr=address;s_awsize=z;s_awlen=n-1;s_awid=id;s_awburst=!fixed_addr;s_awvalid=1;
      do @(posedge clk);while(!s_awready);
      @(negedge clk);s_awvalid=0;
      for(integer b=0;b<n;b=b+1) begin
        a=address+(fixed_addr ? 0 : (b<<z));
        s_wdata=0;s_wstrb=0;
        for(integer j=0;j<(1<<z);j=j+1) begin
          s_wdata[((a+j)&15)*8+:8]=(id*31+b*9+j)&255;
          if(j%3!=1) begin
            s_wstrb[(a+j)&15]=1;
            if(response==0) expected[(a+j)&4095]=(id*31+b*9+j)&255;
          end
        end
        s_wvalid=1;s_wlast=b==n-1;
        do @(posedge clk);while(!s_wready);
        @(negedge clk);s_wvalid=0;
      end
      while(!s_bvalid) @(negedge clk);
      repeat(5) begin
        if(s_bid!==id[3:0] || s_bresp!==response) $fatal(1,"B response/id mismatch");
        @(negedge clk);
      end
      s_bready=1;@(negedge clk);s_bready=0;
    end
  endtask
  task automatic read_burst(input integer address,z,n,id,input bit fixed_addr,input [1:0] response);
    integer a;
    reg [127:0] value;
    begin
      @(negedge clk);s_araddr=address;s_arsize=z;s_arlen=n-1;s_arid=id;s_arburst=!fixed_addr;s_arvalid=1;
      do @(posedge clk);while(!s_arready);
      @(negedge clk);s_arvalid=0;
      for(integer b=0;b<n;b=b+1) begin
        a=address+(fixed_addr ? 0 : (b<<z));value=0;
        for(integer j=0;j<16;j=j+1) if(response==0) value[j*8+:8]=expected[((a&~15)+j)&4095];
        while(!s_rvalid) @(negedge clk);
        repeat(3) begin
          if(s_rid!==id[3:0] || s_rresp!==response || s_rlast!==(b==n-1) || s_rdata!==value)
            $fatal(1,"R mismatch a=%h b=%0d data=%h expected=%h",a,b,s_rdata,value);
          @(negedge clk);
        end
        s_rready=1;@(negedge clk);s_rready=0;beats=beats+1;
      end
    end
  endtask
  initial begin
    for(integer j=0;j<4096;j=j+1) expected[j]=0;
    repeat(20) @(negedge clk);reset=0;repeat(60) @(negedge clk);
    for(integer z=0;z<=4;z=z+1) begin
      write_burst(32'h80000100+(1<<z),z,7,z+1,0,0);
      read_burst(32'h80000100+(1<<z),z,7,15-z,0,0);
      write_burst(32'h80000200+(1<<z),z,5,z+6,1,0);
      read_burst(32'h80000200+(1<<z),z,5,10-z,1,0);
    end
    // Independent read/write paths and IDs under external stalls.
    fork
      write_burst(32'h80000400,4,16,3,0,0);
      read_burst(32'h80000100,4,8,7,0,0);
    join
    read_burst(32'h80000400,4,16,8,0,0);
    write_burst(32'h90000000,3,4,2,0,2);
    read_burst(32'h90000000,3,4,4,0,2);
    write_burst(32'h80000ff0,4,2,1,0,2);
    read_burst(32'h80000ff0,4,2,1,0,2);
    $display("PASS BOARD_CDC: sizes 8..128 bits, INCR/FIXED, strobes, concurrent R/W, stalls, IDs, range/4KiB rejection; read beats=%0d",beats);
    $finish;
  end
  initial begin #10000000;$fatal(1,"Adapter watchdog");end
endmodule
