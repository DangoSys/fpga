module tb;
  logic signed [19:0] value20;
  logic signed [31:0] value32;
  logic [4:0] amount;
  wire signed [19:0] actual20, original20;
  wire signed [31:0] actual32, original32;
  RoundShiftChecks dut(.*);
  integer comparisons = 0;
  logic [63:0] rng = 64'h17339cab28eaf641;

  // Independent oracle: magnitude division/remainder, not a barrel-shift copy.
  function automatic longint signed nearest_even(input longint signed v,
                                                input integer s);
    longint signed magnitude, divisor, quotient, remainder;
    if (s == 0) return v;
    magnitude = v < 0 ? -v : v;
    divisor = 64'sd1 << s;
    quotient = magnitude / divisor;
    remainder = magnitude % divisor;
    if (2 * remainder > divisor ||
        (2 * remainder == divisor && quotient % 2 != 0)) quotient++;
    return v < 0 ? -quotient : quotient;
  endfunction

  task automatic check(input longint signed v, input integer s);
    longint signed expected20, expected32;
    value20 = v[19:0];
    value32 = v[31:0];
    amount = s[4:0];
    #1;
    expected20 = nearest_even(longint'(value20), s);
    expected32 = nearest_even(longint'(value32), s);
    if (actual20 !== expected20[19:0] || actual32 !== expected32[31:0] ||
        actual20 !== original20 || actual32 !== original32)
      $fatal(1, "RNE v=%0d s=%0d actual20=%0d gold20=%0d actual32=%0d gold32=%0d",
        v, s, actual20, expected20, actual32, expected32);
    comparisons += 2;
  endtask

  initial begin
    for (integer s = 0; s < 32; s++) begin
      check(0, s); check(1, s); check(-1, s);
      check(2147483647, s); check(-2147483648, s);
      check(524287, s); check(-524288, s);
      if (s > 0) begin
        // Halfway and adjacent values on either side, odd/even positive/negative.
        for (integer q = -6; q <= 6; q++)
          for (integer delta = -1; delta <= 1; delta++)
            check(q * (64'sd1 << s) + (64'sd1 << (s - 1)) + delta, s);
      end
    end
    for (integer i = 0; i < 200000; i++) begin
      rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
      check(longint'(int'(rng[31:0])), int'(rng[36:32]));
    end
    $display("PASS ROUND_SHIFT comparisons=%0d widths=20,32 shifts=0..31", comparisons);
    $finish;
  end
endmodule
