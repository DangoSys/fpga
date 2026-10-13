module FpuRfOriginal(
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

  reg [64:0] Memory[0:31];
  always @(posedge W0_clk) begin
    if (W0_en & 1'h1)
      Memory[W0_addr] <= W0_data;
    if (W1_en & 1'h1)
      Memory[W1_addr] <= W1_data;
  end // always @(posedge)
  assign R0_data = R0_en ? Memory[R0_addr] : 65'bx;
  assign R1_data = R1_en ? Memory[R1_addr] : 65'bx;
  assign R2_data = R2_en ? Memory[R2_addr] : 65'bx;
endmodule
