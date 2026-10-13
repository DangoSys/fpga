module tb;
  reg clock = 0, reset = 1;
  wire passed;
  integer cycles = 0;
  SubRobCheck dut(.*);
  always #5 clock = ~clock;
  initial begin repeat(5) @(negedge clock); reset=0; end
  always @(posedge clock) if (!reset) begin
    cycles <= cycles + 1;
    if (passed) begin
      $display("PASS SUBROB streaming rows=40 commands=39 cycles=%0d", cycles);
      $finish;
    end
    if (cycles > 10000) $fatal(1, "SubROB timeout");
  end
endmodule
