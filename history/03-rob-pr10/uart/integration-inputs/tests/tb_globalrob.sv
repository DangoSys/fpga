`timescale 1ns/1ps
module tb;
  reg clock = 0, reset = 1;
  reg [31:0] seed = 32'h12345678;
  wire passed;
  integer cycles = 0;
  GlobalRobCheck dut(.*);
  always #5 clock = ~clock;
  initial begin
    repeat (5) @(negedge clock);
    reset = 0;
    repeat (1200) @(negedge clock);
    reset = 1; seed = 32'hda7a0319;
    repeat (5) @(negedge clock);
    reset = 0;
    repeat (1800) @(negedge clock);
    reset = 1; seed = 32'habcdef01;
    repeat (5) @(negedge clock);
    reset = 0;
  end
  always @(posedge clock) begin
    cycles <= cycles + 1;
    if (!reset && passed) begin
      $display("PASS GLOBALROB RAM/register cycle comparison, payloads, wrap, stalls, resets cycles=%0d", cycles);
      $finish;
    end
    if (cycles > 15000) $fatal(1, "GlobalROB test timeout");
  end
endmodule
