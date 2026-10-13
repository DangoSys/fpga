`timescale 1ns/1ps
module tb;
  reg clock=0, reset=1;
  wire passed;
  RoutingCheck dut(.*);
  always #5 clock=~clock;
  initial begin
    repeat(10) @(negedge clock);
    reset=0;
    wait(passed);
    $display("PASS fixed routing: 512 transactions, DMA arbitration, stalls");
    $finish;
  end
  initial begin
    repeat(20000) @(posedge clock);
    $fatal(1, "Routing check timeout");
  end
endmodule
