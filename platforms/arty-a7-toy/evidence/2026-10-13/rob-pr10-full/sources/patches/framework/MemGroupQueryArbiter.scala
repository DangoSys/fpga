package framework.memdomain.frontend

import chisel3._
import chisel3.util._

class MemGroupQuery(val bankWidth: Int) extends Bundle {
  val bank = UInt(bankWidth.W)
  val shared = Bool()
}

/** Own the two-cycle backend lookup until the selected client accepts its reply. */
class MemGroupQueryArbiter(bankWidth: Int, countWidth: Int) extends Module {
  val io = IO(new Bundle {
    val request = Vec(2, Flipped(Decoupled(new MemGroupQuery(bankWidth))))
    val response = Vec(2, Decoupled(UInt(countWidth.W)))
    val backendBank = Output(UInt(bankWidth.W))
    val backendShared = Output(Bool())
    val backendCount = Input(UInt(countWidth.W))
  })
  val idle :: waitFirst :: waitSecond :: reply :: Nil = Enum(4)
  val state = RegInit(idle)
  val owner = RegInit(0.U(1.W))
  val address = RegInit(0.U.asTypeOf(new MemGroupQuery(bankWidth)))
  val count = RegInit(0.U(countWidth.W))
  val arbiter = Module(new RRArbiter(new MemGroupQuery(bankWidth), 2))
  arbiter.io.in <> io.request
  arbiter.io.out.ready := state === idle
  val query = Mux(state === idle, arbiter.io.out.bits, address)
  io.backendBank := query.bank
  io.backendShared := query.shared
  for (i <- 0 until 2) {
    io.response(i).valid := state === reply && owner === i.U
    io.response(i).bits := count
  }
  when(arbiter.io.out.fire) {
    owner := arbiter.io.chosen
    address := arbiter.io.out.bits
    state := waitFirst
  }
  when(state === waitFirst) { state := waitSecond }
  when(state === waitSecond) {
    count := io.backendCount
    state := reply
  }
  when(io.response(owner).fire) { state := idle }
}
