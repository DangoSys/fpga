`timescale 1ns/1ps
module tb;
  reg clock=0;
  reg reset=0;
  reg interrupt=0;
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
  ToyLinuxChip dut(.*);
  integer cycle_count=0;
  always @(posedge clock) if (!reset) cycle_count<=cycle_count+1;
  always #5 clock=~clock;
  initial begin reset=1; repeat(20) @(negedge clock); reset=0; end
  initial begin repeat(5000000) @(posedge clock); $fatal(1,"CPU timeout"); end
  axi_smoke_memory #(.DATA_BITS(128), .ID_BITS(4), .ADDR_BITS(32), .BASE(32'h80000000), .CAPACITY(262144), .IMAGE("smoke.hex")) memory_model (
    .clock(clock),
    .reset(reset),
    .aw_ready(memory_aw_ready),
    .aw_valid(memory_aw_valid),
    .aw_bits_id(memory_aw_bits_id),
    .aw_bits_addr(memory_aw_bits_addr),
    .aw_bits_len(memory_aw_bits_len),
    .aw_bits_size(memory_aw_bits_size),
    .aw_bits_burst(memory_aw_bits_burst),
    .w_ready(memory_w_ready),
    .w_valid(memory_w_valid),
    .w_bits_data(memory_w_bits_data),
    .w_bits_strb(memory_w_bits_strb),
    .w_bits_last(memory_w_bits_last),
    .b_ready(memory_b_ready),
    .b_valid(memory_b_valid),
    .b_bits_id(memory_b_bits_id),
    .b_bits_resp(memory_b_bits_resp),
    .ar_ready(memory_ar_ready),
    .ar_valid(memory_ar_valid),
    .ar_bits_id(memory_ar_bits_id),
    .ar_bits_addr(memory_ar_bits_addr),
    .ar_bits_len(memory_ar_bits_len),
    .ar_bits_size(memory_ar_bits_size),
    .ar_bits_burst(memory_ar_bits_burst),
    .r_ready(memory_r_ready),
    .r_valid(memory_r_valid),
    .r_bits_id(memory_r_bits_id),
    .r_bits_data(memory_r_bits_data),
    .r_bits_resp(memory_r_bits_resp),
    .r_bits_last(memory_r_bits_last)
  );
  axi_smoke_memory #(.DATA_BITS(64), .ID_BITS(2), .ADDR_BITS(31), .BASE(32'h60000000), .CAPACITY(4096), .MONITOR(1), .TEST_LABEL("whole Toy Gemmini regression")) peripherals_model (
    .clock(clock),
    .reset(reset),
    .aw_ready(peripherals_aw_ready),
    .aw_valid(peripherals_aw_valid),
    .aw_bits_id(peripherals_aw_bits_id),
    .aw_bits_addr(peripherals_aw_bits_addr),
    .aw_bits_len(peripherals_aw_bits_len),
    .aw_bits_size(peripherals_aw_bits_size),
    .aw_bits_burst(peripherals_aw_bits_burst),
    .w_ready(peripherals_w_ready),
    .w_valid(peripherals_w_valid),
    .w_bits_data(peripherals_w_bits_data),
    .w_bits_strb(peripherals_w_bits_strb),
    .w_bits_last(peripherals_w_bits_last),
    .b_ready(peripherals_b_ready),
    .b_valid(peripherals_b_valid),
    .b_bits_id(peripherals_b_bits_id),
    .b_bits_resp(peripherals_b_bits_resp),
    .ar_ready(peripherals_ar_ready),
    .ar_valid(peripherals_ar_valid),
    .ar_bits_id(peripherals_ar_bits_id),
    .ar_bits_addr(peripherals_ar_bits_addr),
    .ar_bits_len(peripherals_ar_bits_len),
    .ar_bits_size(peripherals_ar_bits_size),
    .ar_bits_burst(peripherals_ar_bits_burst),
    .r_ready(peripherals_r_ready),
    .r_valid(peripherals_r_valid),
    .r_bits_id(peripherals_r_bits_id),
    .r_bits_data(peripherals_r_bits_data),
    .r_bits_resp(peripherals_r_bits_resp),
    .r_bits_last(peripherals_r_bits_last)
  );
  final $display("MEASURE cycles=%0d memory_reads=%0d memory_writes=%0d", cycle_count, memory_model.read_bursts, memory_model.write_bursts);
endmodule
