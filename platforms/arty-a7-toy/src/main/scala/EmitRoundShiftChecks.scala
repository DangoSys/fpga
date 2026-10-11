package fpga.arty.linux

import chisel3._
import circt.stage.ChiselStage
import gemmini._

/** Check both the existing PE width and the final WS accumulator width. */
class RoundShiftChecks extends RawModule {
  val value20 = IO(Input(SInt(20.W)))
  val value32 = IO(Input(SInt(32.W)))
  val amount = IO(Input(UInt(5.W)))
  val actual20 = IO(Output(SInt(20.W)))
  val actual32 = IO(Output(SInt(32.W)))
  val original20 = IO(Output(SInt(20.W)))
  val original32 = IO(Output(SInt(32.W)))
  import Arithmetic.SIntArithmetic._
  actual20 := FpgaRoundShift(value20, amount)
  actual32 := FpgaRoundShift(value32, amount)
  original20 := cast(value20.pad(32)).>>(amount).clippedToWidthOf(0.S(20.W))
  original32 := cast(value32).>>(amount).clippedToWidthOf(0.S(32.W))
}

object EmitRoundShiftChecks extends App {
  ChiselStage.emitSystemVerilogFile(new RoundShiftChecks,
    Array("--target-dir", "build/round-check"),
    Array("-disable-all-randomization", "-strip-debug-info"))
}
