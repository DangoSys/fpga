`timescale 1ns/1ps
module tb;
  reg clk = 0;
  always #5 clk = ~clk;
  reg [4:0] ra0 = 0, ra1 = 0, ra2 = 0, wa0 = 0, wa1 = 0;
  reg re0 = 0, re1 = 0, re2 = 0, we0 = 0, we1 = 0;
  reg [64:0] wd0 = 0, wd1 = 0;
  wire [64:0] old0, old1, old2, new0, new1, new2;
  reg [64:0] expected [0:31];
  reg [31:0] valid = 0;
  integer seed = 99127;
  integer comparisons = 0, dual_writes = 0, same_address_writes = 0;

  FpuRfOriginal original(
    .R0_addr(ra0), .R0_en(re0), .R0_clk(clk), .R0_data(old0),
    .R1_addr(ra1), .R1_en(re1), .R1_clk(clk), .R1_data(old1),
    .R2_addr(ra2), .R2_en(re2), .R2_clk(clk), .R2_data(old2),
    .W0_addr(wa0), .W0_en(we0), .W0_clk(clk), .W0_data(wd0),
    .W1_addr(wa1), .W1_en(we1), .W1_clk(clk), .W1_data(wd1)
  );
  FpuRfLvt candidate(
    .R0_addr(ra0), .R0_en(re0), .R0_clk(clk), .R0_data(new0),
    .R1_addr(ra1), .R1_en(re1), .R1_clk(clk), .R1_data(new1),
    .R2_addr(ra2), .R2_en(re2), .R2_clk(clk), .R2_data(new2),
    .W0_addr(wa0), .W0_en(we0), .W0_clk(clk), .W0_data(wd0),
    .W1_addr(wa1), .W1_en(we1), .W1_clk(clk), .W1_data(wd1)
  );

  function [64:0] random_data;
    reg [31:0] lo, hi, extra;
    begin
      lo = $random(seed); hi = $random(seed); extra = $random(seed);
      random_data = {extra[0], hi, lo};
    end
  endfunction

  task check;
    begin
      if (re0 && valid[ra0]) begin
        if (old0 !== expected[ra0] || new0 !== expected[ra0])
          $fatal(1, "R0 mismatch at %0d", ra0);
        comparisons = comparisons + 1;
      end
      if (re1 && valid[ra1]) begin
        if (old1 !== expected[ra1] || new1 !== expected[ra1])
          $fatal(1, "R1 mismatch at %0d", ra1);
        comparisons = comparisons + 1;
      end
      if (re2 && valid[ra2]) begin
        if (old2 !== expected[ra2] || new2 !== expected[ra2])
          $fatal(1, "R2 mismatch at %0d", ra2);
        comparisons = comparisons + 1;
      end
    end
  endtask

  task edge_and_check;
    begin
      #1; check();
      @(posedge clk);
      if (we0) begin expected[wa0] = wd0; valid[wa0] = 1; end
      if (we1) begin expected[wa1] = wd1; valid[wa1] = 1; end
      if (we0 && we1) begin
        dual_writes = dual_writes + 1;
        if (wa0 == wa1) same_address_writes = same_address_writes + 1;
      end
      #1; check();
      // Asynchronous reads must follow new addresses without a clock edge.
      ra0 = ra0 + 1; ra1 = ra1 + 3; ra2 = ra2 + 7;
      #1; check();
    end
  endtask

  initial begin
    for (integer i = 0; i < 32; i = i + 1) begin
      @(negedge clk);
      wa0 = i; we0 = 1; we1 = 0; wd0 = random_data();
      re0 = 1; re1 = 1; re2 = 1;
      edge_and_check();
    end
    for (integer i = 0; i < 20000; i = i + 1) begin
      @(negedge clk);
      wa0 = $random(seed); wa1 = $random(seed);
      if (i % 4 == 0) wa1 = wa0;
      we0 = (i % 8 != 0); we1 = (i % 8 != 1);
      wd0 = random_data(); wd1 = random_data();
      ra0 = wa0; ra1 = wa1; ra2 = $random(seed);
      re0 = (i % 5 != 0); re1 = (i % 5 != 1); re2 = (i % 5 != 2);
      edge_and_check();
    end
    if (dual_writes < 10000 || same_address_writes < 2000 || comparisons < 100000)
      $fatal(1, "Insufficient conflict/asynchronous read coverage");
    $display("PASS FPU_RF_LVT cycles=20032 comparisons=%0d dual_writes=%0d same_address_writes=%0d",
      comparisons, dual_writes, same_address_writes);
    $finish;
  end
  initial begin #1000000; $fatal(1, "RF test timeout"); end
endmodule
