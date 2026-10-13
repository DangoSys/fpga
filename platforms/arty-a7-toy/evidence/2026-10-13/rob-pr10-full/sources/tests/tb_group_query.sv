module tb;
  reg clock = 0;
  reg reset = 1;
  wire passed;
  GroupQueryCheck dut(.clock(clock), .reset(reset), .passed(passed));
  always #5 clock = ~clock;
  initial begin
    repeat (5) @(negedge clock);
    reset = 0;
    wait(passed);
    @(negedge clock);
    reset = 1;
    repeat (5) @(negedge clock);
    reset = 0;
    wait(passed);
    $display("PASS: 256 concurrent group queries, stalls, shared/private selection, reset and repeat");
    $finish;
  end
  initial begin
    #200000;
    $fatal(1, "Group query timeout");
  end
endmodule
