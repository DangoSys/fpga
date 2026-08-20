// dpi_stubs.sv — DPI 仿真模块的综合空壳（全部只读，不参与电路逻辑）

module CTraceDPI(
  input clock, input reset,
  input [7:0] subcmd, input [31:0] ctr_id,
  input [63:0] tag, input [63:0] elapsed, input [63:0] cycle,
  input enable
);
endmodule

module ITraceDPI(
  input clock, input reset,
  input [7:0] is_issue, input [31:0] rob_id, input [31:0] domain_id, input [31:0] funct,
  input [63:0] pc, input [63:0] rs1_idx, input [63:0] rs2_idx,
  input [63:0] rs1_data, input [63:0] rs2_data, input [7:0] bank_enable,
  input enable
);
endmodule

module MTraceDPI(
  input clock, input reset,
  input [7:0] is_write, input [7:0] is_shared, input [31:0] channel,
  input [63:0] hart_id, input [31:0] rob_id, input [31:0] vbank_id, input [31:0] pbank_id,
  input [31:0] group_id, input [31:0] addr, input [31:0] write_mask,
  input [63:0] data_lo, input [63:0] data_hi,
  input enable
);
endmodule

module MTraceIssueDPI(
  input clock, input reset,
  input [63:0] hart_id, input [7:0] is_shared, input [31:0] rob_id,
  input [31:0] vbank_id, input [31:0] group_id,
  input enable
);
endmodule

module MemPMCTraceDPI(
  input clock, input reset,
  input [7:0] is_store, input [31:0] rob_id, input [63:0] elapsed,
  input enable
);
endmodule

module PMCTraceDPI(
  input clock, input reset,
  input [31:0] ball_id, input [31:0] rob_id, input [63:0] elapsed,
  input enable
);
endmodule

module SCUReadDPI(
  input clock, input reset, input [31:0] hart_id, input enable, input pop,
  output rx_valid, output [7:0] rx_data
);
  assign rx_valid = 1'b0;
  assign rx_data  = 8'h0;
endmodule

module SCUWriteDPI(
  input clock, input reset,
  input [31:0] uart_hart_id, input uart_valid, input [7:0] uart_data,
  input [31:0] exit_hart_id, input exit_valid, input [31:0] exit_code
);
endmodule

module plusarg_reader #(
  parameter FORMAT = "borked=%d",
  parameter WIDTH = 1,
  parameter [WIDTH-1:0] DEFAULT = 0
) (
  output [WIDTH-1:0] out
);
  assign out = DEFAULT;
endmodule
