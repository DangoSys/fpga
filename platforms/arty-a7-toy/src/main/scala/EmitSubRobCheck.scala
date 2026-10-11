package fpga.arty.linux

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage
import framework.frontend.globalrs.SubROB

/** Stream more than the FIFO depth, including empty rows and stalled completion. */
class SubRobCheck extends Module {
  val passed = IO(Output(Bool()))
  val sub = Module(new SubROB(OriginalToy.serial))
  val cycle = RegInit(0.U(16.W))
  cycle := cycle + 1.U
  assert(cycle < 10000.U, "SubROB streaming timeout")
  val sent = RegInit(0.U(6.W))
  val issued = RegInit(0.U(6.W))
  val completed = RegInit(0.U(6.W))
  val masters = RegInit(0.U(2.W))
  val expected = (0 until 40).flatMap { row =>
    if (row % 3 == 0) Seq.empty else if (row % 3 == 1) Seq(row * 4) else Seq(row * 4, row * 4 + 1)
  }
  val commands = VecInit(expected.map(_.U(32.W)))
  sub.io.write.valid := sent < 40.U
  sub.io.write.bits := 0.U.asTypeOf(sub.io.write.bits)
  sub.io.write.bits.master_rob_id := 3.U
  sub.io.write.bits.ball_id := 0.U
  for (slot <- 0 until 4) {
    sub.io.write.bits.slots(slot).valid :=
      (if (slot == 0) sent % 3.U =/= 0.U else if (slot == 1) sent % 3.U === 2.U else false.B)
    sub.io.write.bits.slots(slot).cmd.cmd.raw_inst := sent * 4.U + slot.U
  }
  when(sub.io.write.fire) { sent := sent + 1.U }
  val pending = Module(new Queue(UInt(5.W), 8))
  sub.io.issue.ready := pending.io.enq.ready && cycle(0)
  pending.io.enq.valid := sub.io.issue.fire
  pending.io.enq.bits := sub.io.issueSubId
  sub.io.subComplete.valid := pending.io.deq.valid && cycle(1)
  sub.io.subComplete.bits := pending.io.deq.bits
  pending.io.deq.ready := sub.io.subComplete.ready && cycle(1)
  when(sub.io.issue.fire) {
    assert(issued < expected.size.U)
    assert(sub.io.issue.bits.cmd.raw_inst === commands(issued), "SubROB dropped/reordered a row")
    issued := issued + 1.U
  }
  when(sub.io.subComplete.fire) { completed := completed + 1.U }
  sub.io.masterComplete.ready := cycle(2)
  when(sub.io.masterComplete.fire) {
    assert(sent === 40.U && issued === expected.size.U && completed === expected.size.U,
      "SubROB completed master before all accepted rows were executed")
    masters := masters + 1.U
  }
  passed := masters === 1.U
}

object EmitSubRobCheck extends App {
  ChiselStage.emitSystemVerilogFile(new SubRobCheck,
    Array("--target-dir", args.headOption.getOrElse("build/subrob-check")),
    Array("-disable-all-randomization", "-strip-debug-info"))
}
