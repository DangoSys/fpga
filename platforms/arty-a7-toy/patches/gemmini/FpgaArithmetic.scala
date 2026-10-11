package gemmini

import chisel3._
import chisel3.util._

/** Signed round-to-nearest-even. Two low bits carry guard and sticky state. */
object FpgaRoundShift {
  def apply(value: SInt, amount: UInt): SInt = {
    require(Set(20, 32)(value.getWidth) && amount.getWidth == 5)
    val width = value.getWidth + 2
    var stage = Cat(value.asUInt, 0.U(2.W))
    for (bit <- 0 until amount.getWidth) {
      val distance = 1 << bit
      val shifted = (stage.asSInt >> distance).pad(width).asUInt
      val jammed = Cat(shifted(width - 1, 1), shifted(0) || stage(distance - 1, 0).orR)
      stage = Mux(amount(bit), jammed, stage)
    }
    val integer = stage(width - 1, 2).asSInt
    val increment = stage(1) && (stage(0) || stage(2))
    // Rounding a right shift cannot overflow the original signed input range.
    (integer + Mux(increment, 1.S(value.getWidth.W), 0.S(value.getWidth.W))).asSInt
  }
}

/** No added registers: preserves the original PE cycle interface. */
class FpgaDspMac extends BlackBox with HasBlackBoxInline {
  val io = IO(new Bundle {
    val a = Input(UInt(8.W))
    val b = Input(UInt(8.W))
    val c = Input(UInt(20.W))
    val y = Output(UInt(20.W))
  })
  setInline("FpgaDspMac.v", """
module FpgaDspMac(input [7:0] a, b, input [19:0] c, output [19:0] y);
  (* use_dsp = "yes" *) wire signed [19:0] result;
  assign result = $signed(a) * $signed(b) + $signed(c);
  assign y = result;
endmodule
""")
}
