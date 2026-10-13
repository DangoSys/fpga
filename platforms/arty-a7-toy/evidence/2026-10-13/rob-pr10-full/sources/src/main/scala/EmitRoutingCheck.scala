package fpga.arty.linux

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage
import framework.memdomain.midend.MemMidend
import framework.memdomain.backend.accpipe.AccPipe

// Real routing and AccPipe modules, with independently checked SRAM endpoints.
// Stalls cover request acceptance, SRAM response, and final response consumption.
class RoutingCheck extends Module {
  val passed = IO(Output(Bool()))
  val b = OriginalToy.serial
  val midend = Module(new MemMidend(b))
  val cycle = RegInit(0.U(16.W))
  cycle := cycle + 1.U
  assert(cycle < 20000.U, "Routing regression timeout")
  midend.io.hartid := 0.U
  midend.io.inst_ids.zipWithIndex.foreach { case (id, index) => id := (100 + index).U }
  val readSent = RegInit(VecInit(Seq.fill(3)(0.U(7.W))))
  val readSeen = RegInit(VecInit(Seq.fill(3)(0.U(7.W))))
  val writeSent = RegInit(VecInit(Seq.fill(5)(0.U(7.W))))
  val writeSeen = RegInit(VecInit(Seq.fill(5)(0.U(7.W))))
  val ballAccepted = readSent.take(2).map(_ === 64.U).reduce(_ && _) &&
    writeSent.take(4).map(_ === 64.U).reduce(_ && _)
  // Release the Ball as soon as its final requests are accepted, while responses
  // can still be in flight. Fixed routes must keep delivering these responses.
  midend.io.ballChannelActive(0) := !ballAccepted
  for (port <- 0 until 3) {
    val source = midend.io.bankRead(port)
    val bank = if (port < 2) port else 6
    source.is_shared := false.B
    source.bankRead.bank_id := bank.U
    source.bankRead.group_id := 0.U
    source.bankRead.ball_id := 0.U
    source.bankRead.rob_id := (port % 4).U
    source.bankRead.io.req.valid := readSent(port) < 64.U
    source.bankRead.io.req.bits.addr := readSent(port)
    source.bankRead.io.resp.ready := cycle((port + 1) % 5)
    when(source.bankRead.io.req.fire) { readSent(port) := readSent(port) + 1.U }
    when(source.bankRead.io.resp.fire) {
      assert(source.bankRead.io.resp.bits.data ===
        (readSeen(port) + (bank << 16).U), "Read response lost or misrouted")
      readSeen(port) := readSeen(port) + 1.U
    }
  }
  for (port <- 0 until 5) {
    val source = midend.io.bankWrite(port)
    val bank = if (port < 4) port + 2 else 7
    source.is_shared := false.B
    source.bankWrite.bank_id := bank.U
    source.bankWrite.group_id := (port % 4).U
    source.bankWrite.ball_id := 0.U
    source.bankWrite.rob_id := (port % 4).U
    source.bankWrite.io.req.valid := writeSent(port) < 64.U &&
      (if (port == 4) cycle >= 1.U else true.B)
    source.bankWrite.io.req.bits.addr := writeSent(port)
    source.bankWrite.io.req.bits.data := writeSent(port) + (bank << 16).U
    source.bankWrite.io.req.bits.mask := VecInit(Seq.fill(b.memDomain.bankMaskLen)(true.B))
    source.bankWrite.io.resp.ready := cycle((port + 2) % 5)
    when(source.bankWrite.io.req.fire) { writeSent(port) := writeSent(port) + 1.U }
    when(source.bankWrite.io.resp.fire) {
      assert(source.bankWrite.io.resp.bits.ok, "Write response lost or misrouted")
      writeSeen(port) := writeSeen(port) + 1.U
    }
  }
  for (channel <- 0 until 7) {
    val request = midend.io.mem_req(channel)
    val pipe = Module(new AccPipe(b))
    pipe.io.mem_req <> request
    pipe.io.is_multi := false.B
    val readPending = RegInit(false.B)
    val writePending = RegInit(false.B)
    val readData = Reg(UInt(b.memDomain.bankWidth.W))
    val routePending = RegInit(false.B)
    val routeBank = Reg(UInt(b.memDomain.vbankIdWidth.W))
    when(!routePending && !pipe.io.busy &&
        (request.read.req.valid || request.write.req.valid)) {
      routePending := true.B
      routeBank := request.bank_id
    }
    when(request.read.req.fire || request.write.req.fire) { routePending := false.B }
    pipe.io.sramRead.req.ready := routePending && !readPending && !writePending && cycle(channel % 5)
    pipe.io.sramWrite.req.ready := routePending && !readPending && !writePending && cycle((channel + 1) % 5)
    pipe.io.sramRead.resp.valid := readPending && cycle((channel + 3) % 5)
    pipe.io.sramRead.resp.bits.data := readData
    pipe.io.sramWrite.resp.valid := writePending && cycle((channel + 4) % 5)
    pipe.io.sramWrite.resp.bits.ok := true.B
    when(pipe.io.sramRead.req.fire) {
      readPending := true.B
      readData := pipe.io.sramRead.req.bits.addr + (routeBank << 16)
      assert(request.bank_id === routeBank, "Route metadata changed before SRAM acceptance")
      assert(request.bank_id === (if (channel < 2) channel else 6).U)
      assert(request.group_id === 0.U)
      assert(request.rob_id === (if (channel < 2) channel else 2).U)
      assert(request.inst_id === (if (channel < 2) 100 + channel else 102).U)
    }
    when(pipe.io.sramWrite.req.fire) {
      writePending := true.B
      assert(request.bank_id === routeBank, "Write replaced a pending read route")
      val bank = if (channel < 6) channel else 7
      assert(request.bank_id === bank.U, "Wrong write bank metadata")
      assert(pipe.io.sramWrite.req.bits.data ===
        (pipe.io.sramWrite.req.bits.addr + (bank << 16).U))
      assert(pipe.io.sramWrite.req.bits.mask.asUInt.andR)
      val port = if (channel < 6) math.max(0, channel - 2) else 4
      assert(request.group_id === (port % 4).U)
      assert(request.rob_id === (port % 4).U)
      assert(request.inst_id === (100 + port % 4).U)
    }
    when(pipe.io.sramRead.resp.fire) { readPending := false.B }
    when(pipe.io.sramWrite.resp.fire) { writePending := false.B }
    assert(!(pipe.io.sramRead.req.fire && pipe.io.sramWrite.req.fire))
  }
  passed := (readSeen ++ writeSeen).map(_ === 64.U).reduce(_ && _)
}

object EmitRoutingCheck extends App {
  ChiselStage.emitSystemVerilogFile(new RoutingCheck,
    args = Array("--target-dir", args.head),
    firtoolOpts = Array("-disable-all-randomization", "-strip-debug-info"))
}
