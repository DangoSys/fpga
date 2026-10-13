package fpga.arty.linux

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage
import framework.frontend.globalrs.GlobalROB
import framework.frontend.decoder.{DomainId, PostGDCmd}
import framework.memdomain.frontend.cmd.decoder.DISA.MSET_BITPAT

/** Cycle comparison of register and synchronous-RAM operand storage. */
class GlobalRobCheck extends Module {
  val seed = IO(Input(UInt(32.W)))
  val passed = IO(Output(Bool()))
  private val b = OriginalToy.serial
  val dut = Module(new GlobalROB(b, useOperandRam = true))
  val reference = Module(new GlobalROB(b, useOperandRam = false))
  val cycle = RegInit(0.U(16.W))
  val random = RegInit(seed)
  cycle := cycle + 1.U
  random := Cat(random(30, 0), random(31) ^ random(21) ^ random(1) ^ random(0))
  assert(cycle < 9000.U, "GlobalROB drain timeout")

  val source = Module(new Queue(new PostGDCmd(b), 2))
  val generated = Wire(new PostGDCmd(b))
  generated := 0.U.asTypeOf(generated)
  val config = random(5, 2) === 0.U
  generated.domain_id := Mux(config || random(2), DomainId.MEM, DomainId.BALL)
  generated.ball_bid := 0.U
  generated.cmd.funct := Mux(config, MSET_BITPAT.value.U(7.W), Mux(random(3), 53.U, 66.U))
  generated.cmd.raw_inst := random
  generated.cmd.pc := Cat(random, ~random)
  generated.cmd.rs1Data := Cat(random, random ^ "h597bdf03".U)
  generated.cmd.rs2Data := Mux(config,
    Cat(random, 0.U(21.W), 1.U(1.W), 0.U(3.W), random(1, 0), 0.U(5.W)),
    Cat(~random, random ^ "h26ac048e".U))
  generated.bankAccess.rd_bank_0_valid := !config && random(8)
  generated.bankAccess.rd_bank_1_valid := !config && random(9)
  generated.bankAccess.wr_bank_valid := config || random(10)
  generated.bankAccess.rd_bank_0_id := random(14, 11)
  generated.bankAccess.rd_bank_1_id := random(18, 15)
  generated.bankAccess.wr_bank_id := random(22, 19)
  source.io.enq.valid := cycle < 5000.U && random(0)
  source.io.enq.bits := generated
  dut.io.alloc <> source.io.deq
  reference.io.alloc.valid := dut.io.alloc.valid
  reference.io.alloc.bits := dut.io.alloc.bits

  val completions = Module(new Queue(UInt(log2Ceil(b.frontend.rob_entries).W), 16))
  val active = cycle(9, 6) === 13.U
  val ready = completions.io.enq.ready && random(7) && cycle(8, 5) =/= 7.U
  dut.io.issue.ready := ready
  reference.io.issue.ready := ready
  completions.io.enq.valid := dut.io.issue.fire
  completions.io.enq.bits := dut.io.issue.bits.rob_id
  dut.io.complete.valid := completions.io.deq.valid && random(4)
  dut.io.complete.bits := completions.io.deq.bits
  reference.io.complete.valid := dut.io.complete.valid
  reference.io.complete.bits := dut.io.complete.bits
  completions.io.deq.ready := dut.io.complete.ready && random(4)
  dut.io.hart_id := 0.U
  reference.io.hart_id := 0.U
  dut.io.subRobActive := active
  reference.io.subRobActive := active

  assert(dut.io.alloc.ready === reference.io.alloc.ready, "ROB allocation timing mismatch")
  assert(dut.io.complete.ready === reference.io.complete.ready, "ROB completion timing mismatch")
  assert(dut.io.issue.valid === reference.io.issue.valid, "ROB issue timing mismatch")
  when(dut.io.issue.valid) {
    assert(dut.io.issue.bits.asUInt === reference.io.issue.bits.asUInt, "ROB issue payload mismatch")
  }
  assert(dut.io.empty === reference.io.empty && dut.io.full === reference.io.full)
  assert(dut.io.head_ptr === reference.io.head_ptr)
  assert(dut.io.issued_count === reference.io.issued_count)
  assert(dut.io.entry_valid.asUInt === reference.io.entry_valid.asUInt)
  assert(dut.io.entry_complete.asUInt === reference.io.entry_complete.asUInt)
  assert(dut.io.inst_ids.asUInt === reference.io.inst_ids.asUInt)

  val allocated = RegInit(0.U(16.W))
  val issued = RegInit(0.U(16.W))
  val completed = RegInit(0.U(16.W))
  val sawFull = RegInit(false.B)
  val sawStall = RegInit(false.B)
  val expected = Reg(Vec(b.frontend.rob_entries, chiselTypeOf(generated.cmd)))
  val allocationSlot = RegInit(0.U(log2Ceil(b.frontend.rob_entries).W))
  when(dut.io.alloc.fire) {
    allocated := allocated + 1.U
    expected(allocationSlot) := dut.io.alloc.bits.cmd
    allocationSlot := Mux(allocationSlot === (b.frontend.rob_entries - 1).U,
      0.U, allocationSlot + 1.U)
  }
  when(dut.io.issue.fire) {
    issued := issued + 1.U
    assert(dut.io.issue.bits.cmd.cmd.asUInt === expected(dut.io.issue.bits.rob_id).asUInt,
      "ROB changed accepted command operands")
  }
  when(dut.io.complete.fire) { completed := completed + 1.U }
  when(dut.io.full) { sawFull := true.B }
  when(dut.io.issue.valid && !ready) { sawStall := true.B }
  passed := cycle > 5005.U && !source.io.deq.valid && dut.io.empty && !completions.io.deq.valid
  when(passed) {
    assert(allocated === issued && issued === completed && allocated > 64.U)
    assert(sawFull && sawStall, "Missing ROB full/stall coverage")
  }
}

object EmitGlobalRobCheck extends App {
  ChiselStage.emitSystemVerilogFile(new GlobalRobCheck,
    Array("--target-dir", args.headOption.getOrElse("build/globalrob-check")),
    Array("-disable-all-randomization", "-strip-debug-info"))
}
