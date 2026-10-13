package fpga.arty.linux

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage
import framework.memdomain.frontend.MemGroupQueryArbiter

class GroupQueryCheck extends Module {
  val passed = IO(Output(Bool()))
  val dut = Module(new MemGroupQueryArbiter(4, 4))
  val cycle = RegInit(0.U(16.W))
  cycle := cycle + 1.U
  assert(cycle < 10000.U, "Group query arbitration timeout")
  def lookup(bank: UInt, shared: Bool): UInt =
    ((bank ^ Mux(shared, 4.U, 0.U))(2, 0) +& 1.U)
  dut.io.backendCount := RegNext(RegNext(lookup(dut.io.backendBank, dut.io.backendShared), 0.U), 0.U)
  val sent = RegInit(VecInit(Seq.fill(2)(0.U(8.W))))
  val received = RegInit(VecInit(Seq.fill(2)(0.U(8.W))))
  for (i <- 0 until 2) {
    val expected = Module(new Queue(UInt(4.W), 4))
    dut.io.request(i).valid := sent(i) < 128.U
    dut.io.request(i).bits.bank := sent(i)(3, 0) ^ (i * 7).U
    dut.io.request(i).bits.shared := sent(i)(4) ^ (i == 1).B
    expected.io.enq.valid := dut.io.request(i).fire
    expected.io.enq.bits := lookup(dut.io.request(i).bits.bank, dut.io.request(i).bits.shared)
    dut.io.response(i).ready := cycle(i + 1) && cycle(0)
    expected.io.deq.ready := dut.io.response(i).fire
    when(dut.io.request(i).fire) {
      assert(expected.io.enq.ready)
      sent(i) := sent(i) + 1.U
    }
    when(dut.io.response(i).valid) {
      assert(expected.io.deq.valid, "Query reply without an accepted request")
      assert(dut.io.response(i).bits === expected.io.deq.bits, "Reply belongs to another bank/client")
    }
    when(dut.io.response(i).fire) { received(i) := received(i) + 1.U }
  }
  passed := received.map(_ === 128.U).reduce(_ && _)
}

object EmitGroupQueryCheck extends App {
  ChiselStage.emitSystemVerilogFile(new GroupQueryCheck,
    Array("--target-dir", args.headOption.getOrElse("build/group-query-check")),
    Array("-disable-all-randomization", "-strip-debug-info"))
}
