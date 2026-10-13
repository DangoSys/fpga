// Port-only fixture from the Chisel-generated core; no CPU behavior.
// Outputs idle at zero. The testbench drives the real platform AXI port.
module ToyLinuxChip(
  input          clock,
                 reset,
                 interrupt,
                 memory_aw_ready,
  output         memory_aw_valid,
  output [3:0]   memory_aw_bits_id,
  output [31:0]  memory_aw_bits_addr,
  output [7:0]   memory_aw_bits_len,
  output [2:0]   memory_aw_bits_size,
  output [1:0]   memory_aw_bits_burst,
  output         memory_aw_bits_lock,
  output [3:0]   memory_aw_bits_cache,
  output [2:0]   memory_aw_bits_prot,
  output [3:0]   memory_aw_bits_qos,
  input          memory_w_ready,
  output         memory_w_valid,
  output [127:0] memory_w_bits_data,
  output [15:0]  memory_w_bits_strb,
  output         memory_w_bits_last,
                 memory_b_ready,
  input          memory_b_valid,
  input  [3:0]   memory_b_bits_id,
  input  [1:0]   memory_b_bits_resp,
  input          memory_ar_ready,
  output         memory_ar_valid,
  output [3:0]   memory_ar_bits_id,
  output [31:0]  memory_ar_bits_addr,
  output [7:0]   memory_ar_bits_len,
  output [2:0]   memory_ar_bits_size,
  output [1:0]   memory_ar_bits_burst,
  output         memory_ar_bits_lock,
  output [3:0]   memory_ar_bits_cache,
  output [2:0]   memory_ar_bits_prot,
  output [3:0]   memory_ar_bits_qos,
  output         memory_r_ready,
  input          memory_r_valid,
  input  [3:0]   memory_r_bits_id,
  input  [127:0] memory_r_bits_data,
  input  [1:0]   memory_r_bits_resp,
  input          memory_r_bits_last,
                 peripherals_aw_ready,
  output         peripherals_aw_valid,
  output [1:0]   peripherals_aw_bits_id,
  output [30:0]  peripherals_aw_bits_addr,
  output [7:0]   peripherals_aw_bits_len,
  output [2:0]   peripherals_aw_bits_size,
  output [1:0]   peripherals_aw_bits_burst,
  output         peripherals_aw_bits_lock,
  output [3:0]   peripherals_aw_bits_cache,
  output [2:0]   peripherals_aw_bits_prot,
  output [3:0]   peripherals_aw_bits_qos,
  input          peripherals_w_ready,
  output         peripherals_w_valid,
  output [63:0]  peripherals_w_bits_data,
  output [7:0]   peripherals_w_bits_strb,
  output         peripherals_w_bits_last,
                 peripherals_b_ready,
  input          peripherals_b_valid,
  input  [1:0]   peripherals_b_bits_id,
                 peripherals_b_bits_resp,
  input          peripherals_ar_ready,
  output         peripherals_ar_valid,
  output [1:0]   peripherals_ar_bits_id,
  output [30:0]  peripherals_ar_bits_addr,
  output [7:0]   peripherals_ar_bits_len,
  output [2:0]   peripherals_ar_bits_size,
  output [1:0]   peripherals_ar_bits_burst,
  output         peripherals_ar_bits_lock,
  output [3:0]   peripherals_ar_bits_cache,
  output [2:0]   peripherals_ar_bits_prot,
  output [3:0]   peripherals_ar_bits_qos,
  output         peripherals_r_ready,
  input          peripherals_r_valid,
  input  [1:0]   peripherals_r_bits_id,
  input  [63:0]  peripherals_r_bits_data,
  input  [1:0]   peripherals_r_bits_resp,
  input          peripherals_r_bits_last
);
  assign memory_aw_valid = '0;
  assign memory_aw_bits_id = '0;
  assign memory_aw_bits_addr = '0;
  assign memory_aw_bits_len = '0;
  assign memory_aw_bits_size = '0;
  assign memory_aw_bits_burst = '0;
  assign memory_aw_bits_lock = '0;
  assign memory_aw_bits_cache = '0;
  assign memory_aw_bits_prot = '0;
  assign memory_aw_bits_qos = '0;
  assign memory_w_valid = '0;
  assign memory_w_bits_data = '0;
  assign memory_w_bits_strb = '0;
  assign memory_w_bits_last = '0;
  assign memory_b_ready = '0;
  assign memory_ar_valid = '0;
  assign memory_ar_bits_id = '0;
  assign memory_ar_bits_addr = '0;
  assign memory_ar_bits_len = '0;
  assign memory_ar_bits_size = '0;
  assign memory_ar_bits_burst = '0;
  assign memory_ar_bits_lock = '0;
  assign memory_ar_bits_cache = '0;
  assign memory_ar_bits_prot = '0;
  assign memory_ar_bits_qos = '0;
  assign memory_r_ready = '0;
  assign peripherals_aw_valid = '0;
  assign peripherals_aw_bits_id = '0;
  assign peripherals_aw_bits_addr = '0;
  assign peripherals_aw_bits_len = '0;
  assign peripherals_aw_bits_size = '0;
  assign peripherals_aw_bits_burst = '0;
  assign peripherals_aw_bits_lock = '0;
  assign peripherals_aw_bits_cache = '0;
  assign peripherals_aw_bits_prot = '0;
  assign peripherals_aw_bits_qos = '0;
  assign peripherals_w_valid = '0;
  assign peripherals_w_bits_data = '0;
  assign peripherals_w_bits_strb = '0;
  assign peripherals_w_bits_last = '0;
  assign peripherals_b_ready = '0;
  assign peripherals_ar_valid = '0;
  assign peripherals_ar_bits_id = '0;
  assign peripherals_ar_bits_addr = '0;
  assign peripherals_ar_bits_len = '0;
  assign peripherals_ar_bits_size = '0;
  assign peripherals_ar_bits_burst = '0;
  assign peripherals_ar_bits_lock = '0;
  assign peripherals_ar_bits_cache = '0;
  assign peripherals_ar_bits_prot = '0;
  assign peripherals_ar_bits_qos = '0;
  assign peripherals_r_ready = '0;
endmodule
