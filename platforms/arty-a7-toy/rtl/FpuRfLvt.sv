module FpuRfLvt(
  input  [4:0]  R0_addr,
  input         R0_en,
                R0_clk,
  output [64:0] R0_data,
  input  [4:0]  R1_addr,
  input         R1_en,
                R1_clk,
  output [64:0] R1_data,
  input  [4:0]  R2_addr,
  input         R2_en,
                R2_clk,
  output [64:0] R2_data,
  input  [4:0]  W0_addr,
  input         W0_en,
                W0_clk,
  input  [64:0] W0_data,
  input  [4:0]  W1_addr,
  input         W1_en,
                W1_clk,
  input  [64:0] W1_data
);

  // Each data bank has one synchronous write port and three asynchronous reads.
  // A 32-bit table identifies the bank containing each register's newest value.
  // Match original W1-over-W0 priority when both ports write the same address.
  // Original RTL clocks both write ports with W0_clk; retain that contract.
  (* ram_style = "distributed" *) reg [64:0] bank0 [0:31];
  (* ram_style = "distributed" *) reg [64:0] bank1 [0:31];
  reg [31:0] latest;
  always @(posedge W0_clk) begin
    if (W0_en) begin
      bank0[W0_addr] <= W0_data;
      latest[W0_addr] <= 1'b0;
    end
    if (W1_en) begin
      bank1[W1_addr] <= W1_data;
      latest[W1_addr] <= 1'b1;
    end
  end
  assign R0_data = R0_en ? (latest[R0_addr] ? bank1[R0_addr] : bank0[R0_addr]) : 65'bx;
  assign R1_data = R1_en ? (latest[R1_addr] ? bank1[R1_addr] : bank0[R1_addr]) : 65'bx;
  assign R2_data = R2_en ? (latest[R2_addr] ? bank1[R2_addr] : bank0[R2_addr]) : 65'bx;
endmodule
