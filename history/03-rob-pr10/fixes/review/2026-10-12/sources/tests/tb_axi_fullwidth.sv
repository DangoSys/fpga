`timescale 1ns/1ps
module tb_axi_fullwidth;
  reg clk=0;always #5 clk=~clk;
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
  axi_fullwidth dut(.*);
  axi_smoke_memory #(.ADDR_BITS(28),.BASE(0),.CAPACITY(4096)) memory (
    .clock(clk),.reset(reset),
    .aw_ready(m_awready),.aw_valid(m_awvalid),.aw_bits_id(m_awid),.aw_bits_addr(m_awaddr),
    .aw_bits_len(m_awlen),.aw_bits_size(m_awsize),.aw_bits_burst(m_awburst),
    .w_ready(m_wready),.w_valid(m_wvalid),.w_bits_data(m_wdata),.w_bits_strb(m_wstrb),.w_bits_last(m_wlast),
    .b_ready(m_bready),.b_valid(m_bvalid),.b_bits_id(m_bid),.b_bits_resp(m_bresp),
    .ar_ready(m_arready),.ar_valid(m_arvalid),.ar_bits_id(m_arid),.ar_bits_addr(m_araddr),
    .ar_bits_len(m_arlen),.ar_bits_size(m_arsize),.ar_bits_burst(m_arburst),
    .r_ready(m_rready),.r_valid(m_rvalid),.r_bits_id(m_rid),.r_bits_data(m_rdata),.r_bits_resp(m_rresp),.r_bits_last(m_rlast));
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
    repeat(5) @(negedge clk);reset=0;
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
    $display("PASS fullwidth AXI: sizes 8..128 bits, INCR/FIXED, strobes, concurrent R/W, stalls, IDs, range/4KiB rejection; read beats=%0d",beats);
    $finish;
  end
  initial begin #2000000;$fatal(1,"Adapter watchdog");end
endmodule
