package fpga.arty.linux

import chisel3._
import circt.stage.ChiselStage
import gemmini._

class QuantizerEquivalence extends RawModule {
  val value = IO(Input(SInt(20.W)))
  val amount = IO(Input(UInt(5.W)))
  val equal = IO(Output(Bool()))
  val reference = IO(Output(SInt(20.W)))
  val actual = IO(Output(SInt(20.W)))
  import Arithmetic.SIntArithmetic._
  reference := cast(value.pad(32)).>>(amount).clippedToWidthOf(0.S(20.W))
  actual := FpgaRoundShift(value, amount)
  equal := reference === actual
}

class PeCycleEquivalence extends Module {
  val original = Module(new ReferencePE(SInt(8.W), SInt(8.W), SInt(20.W), SInt(32.W),
    Dataflow.BOTH, 4))
  val logic = Module(new PE(SInt(8.W), SInt(8.W), SInt(20.W), SInt(32.W),
    Dataflow.BOTH, 4, fpgaDsp = false))
  val dsp = Module(new PE(SInt(8.W), SInt(8.W), SInt(20.W), SInt(32.W),
    Dataflow.BOTH, 4, fpgaDsp = true))
  val in_a = IO(Input(SInt(8.W)))
  val in_b = IO(Input(SInt(20.W)))
  val in_d = IO(Input(SInt(20.W)))
  val control = IO(Input(new PEControl(SInt(32.W))))
  val id = IO(Input(UInt(2.W)))
  val last = IO(Input(Bool()))
  val valid = IO(Input(Bool()))
  // Explicit wiring keeps all three independently emitted implementations.
  original.io.in_a := in_a; logic.io.in_a := in_a; dsp.io.in_a := in_a
  original.io.in_b := in_b; logic.io.in_b := in_b; dsp.io.in_b := in_b
  original.io.in_d := in_d; logic.io.in_d := in_d; dsp.io.in_d := in_d
  original.io.in_control := control; logic.io.in_control := control; dsp.io.in_control := control
  original.io.in_id := id; logic.io.in_id := id; dsp.io.in_id := id
  original.io.in_last := last; logic.io.in_last := last; dsp.io.in_last := last
  original.io.in_valid := valid; logic.io.in_valid := valid; dsp.io.in_valid := valid
  val equal = IO(Output(Bool()))
  equal := (original.io.out_b === logic.io.out_b && original.io.out_c === logic.io.out_c &&
    original.io.out_b === dsp.io.out_b && original.io.out_c === dsp.io.out_c &&
    original.io.out_a === logic.io.out_a && original.io.out_a === dsp.io.out_a &&
    original.io.out_control.asUInt === logic.io.out_control.asUInt &&
    original.io.out_control.asUInt === dsp.io.out_control.asUInt &&
    original.io.out_id === logic.io.out_id && original.io.out_id === dsp.io.out_id &&
    original.io.out_last === logic.io.out_last && original.io.out_last === dsp.io.out_last &&
    original.io.out_valid === logic.io.out_valid && original.io.out_valid === dsp.io.out_valid &&
    original.io.bad_dataflow === logic.io.bad_dataflow && original.io.bad_dataflow === dsp.io.bad_dataflow)
}

object EmitPeChecks extends App {
  val opts = Array("-disable-all-randomization", "-strip-debug-info")
  ChiselStage.emitSystemVerilogFile(new QuantizerEquivalence,
    Array("--target-dir", "build/pe-checks/quantizer"), opts)
  ChiselStage.emitSystemVerilogFile(new PeCycleEquivalence,
    Array("--target-dir", "build/pe-checks/cycles"), opts)
}
