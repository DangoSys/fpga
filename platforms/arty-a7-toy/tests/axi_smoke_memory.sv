// Single outstanding read and write, with independent AXI channels.
// Backpressure is legal: W is accepted after AW; R/B are held until accepted.
module axi_smoke_memory #(
  parameter DATA_BITS=128, ID_BITS=4, ADDR_BITS=32,
  parameter BASE=32'h80000000, CAPACITY=262144,
  parameter IMAGE="", parameter MONITOR=0,
  parameter TEST_LABEL="whole Toy CPU smoke"
) (
  input clock, reset,
  output aw_ready, input aw_valid,
  input [ID_BITS-1:0] aw_bits_id,
  input [ADDR_BITS-1:0] aw_bits_addr,
  input [7:0] aw_bits_len, input [2:0] aw_bits_size,
  input [1:0] aw_bits_burst,
  output w_ready, input w_valid,
  input [DATA_BITS-1:0] w_bits_data,
  input [DATA_BITS/8-1:0] w_bits_strb, input w_bits_last,
  input b_ready, output reg b_valid,
  output reg [ID_BITS-1:0] b_bits_id, output [1:0] b_bits_resp,
  output ar_ready, input ar_valid,
  input [ID_BITS-1:0] ar_bits_id,
  input [ADDR_BITS-1:0] ar_bits_addr,
  input [7:0] ar_bits_len, input [2:0] ar_bits_size,
  input [1:0] ar_bits_burst,
  input r_ready, output reg r_valid,
  output reg [ID_BITS-1:0] r_bits_id,
  output reg [DATA_BITS-1:0] r_bits_data,
  output [1:0] r_bits_resp, output reg r_bits_last
);
  localparam LANES=DATA_BITS/8;
  reg [7:0] mem [0:CAPACITY-1];
  reg write_active;
  reg [ADDR_BITS-1:0] write_addr, read_addr;
  reg [7:0] write_remaining, read_remaining;
  reg [2:0] write_size, read_size;
  reg [3:0] stall_cycle;
  integer read_bursts, write_bursts;
  assign aw_ready = !write_active && !b_valid && stall_cycle[1:0]!=0;
  assign w_ready = write_active && !b_valid && stall_cycle[2:0]!=0;
  assign ar_ready = !r_valid && stall_cycle[1:0]!=1;
  assign b_bits_resp = 0;
  assign r_bits_resp = 0;

  initial begin
    for (integer i=0; i<CAPACITY; i=i+1) mem[i]=0;
    if (IMAGE!="") $readmemh(IMAGE, mem);
  end

  function automatic [DATA_BITS-1:0] read_beat(input [ADDR_BITS-1:0] addr);
    integer offset;
    begin
      offset=(addr & ~(LANES-1))-BASE;
      if (offset<0 || offset+LANES>CAPACITY)
        $fatal(1,"AXI read out of range: %h",addr);
      for (integer lane=0; lane<LANES; lane=lane+1)
        read_beat[lane*8+:8]=mem[offset+lane];
    end
  endfunction

  always @(posedge clock) begin
    if (reset) begin
      stall_cycle<=0;
      read_bursts<=0; write_bursts<=0;
      write_active<=0; b_valid<=0; r_valid<=0;
      b_bits_id<=0; r_bits_id<=0; r_bits_data<=0; r_bits_last<=0;
    end else begin
      stall_cycle<=stall_cycle+1;
      if (b_valid && b_ready) b_valid<=0;
      if (aw_valid && aw_ready) begin
        write_bursts<=write_bursts+1;
        if (aw_bits_burst!=1) $fatal(1,"Expected INCR write burst");
        write_active<=1; write_addr<=aw_bits_addr;
        write_remaining<=aw_bits_len; write_size<=aw_bits_size;
        b_bits_id<=aw_bits_id;
      end
      if (w_valid && w_ready) begin
        integer offset;
        offset=(write_addr & ~(LANES-1))-BASE;
        if (offset<0 || offset+LANES>CAPACITY)
          $fatal(1,"AXI write out of range: %h",write_addr);
        if (w_bits_last != (write_remaining==0)) $fatal(1,"WLAST mismatch");
        for (integer lane=0; lane<LANES; lane=lane+1)
          if (w_bits_strb[lane]) mem[offset+lane]<=w_bits_data[lane*8+:8];
        if (MONITOR && offset==0) begin
          $display("CPU status = %h",w_bits_data);
          if (w_bits_data==64'h600d600d) begin
            $display("PASS %s", TEST_LABEL);
            $finish;
          end
          if ((w_bits_data & 64'hffff0000)==64'hbad00000)
            $fatal(1,"CPU smoke failed at stage %0d",w_bits_data & 64'hffff);
        end
        write_addr<=write_addr+(1<<write_size);
        write_remaining<=write_remaining-1;
        if (write_remaining==0) begin write_active<=0; b_valid<=1; end
      end
      if (ar_valid && ar_ready) begin
        read_bursts<=read_bursts+1;
        if (ar_bits_burst!=1) $fatal(1,"Expected INCR read burst");
        read_addr<=ar_bits_addr; read_remaining<=ar_bits_len;
        read_size<=ar_bits_size; r_bits_id<=ar_bits_id;
        r_bits_data<=read_beat(ar_bits_addr);
        r_bits_last<=(ar_bits_len==0); r_valid<=1;
      end else if (r_valid && r_ready) begin
        if (read_remaining==0) r_valid<=0;
        else begin
          read_addr<=read_addr+(1<<read_size);
          read_remaining<=read_remaining-1;
          r_bits_data<=read_beat(read_addr+(1<<read_size));
          r_bits_last<=(read_remaining==1);
        end
      end
    end
  end
endmodule
