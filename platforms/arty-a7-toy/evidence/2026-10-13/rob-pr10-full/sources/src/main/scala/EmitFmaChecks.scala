package fpga.arty.linux

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage
import org.chipsalliance.cde.config.Parameters
import freechips.rocketchip.tile._
import freechips.rocketchip.subsystem.{TilesLocated, InSubsystem}
import framework.system.tile.BBTileAttachParams

class FmaPrecisionCheck(implicit p: Parameters) extends Module {
  val valid = IO(Input(Bool()))
  val tag = IO(Input(UInt(2.W)))
  val kind = IO(Input(UInt(2.W))) // 0=FMA, 1=add/subtract, 2=multiply
  val op = IO(Input(UInt(2.W)))
  val rm = IO(Input(UInt(3.W)))
  val a = IO(Input(UInt(64.W)))
  val b = IO(Input(UInt(64.W)))
  val c = IO(Input(UInt(64.W)))
  val expected = IO(Output(UInt(64.W)))
  val actual = IO(Output(UInt(64.W)))
  val expectedFlags = IO(Output(UInt(5.W)))
  val actualFlags = IO(Output(UInt(5.W)))
  val outValid = IO(Output(Bool()))
  val equal = IO(Output(Bool()))
  val types = Seq(FType.H, FType.S, FType.D)
  val inputs = types.zipWithIndex.map { case (t, index) =>
    val in = Wire(new FPInput)
    in := 0.U.asTypeOf(new FPInput)
    in.ren3 := kind === 0.U
    in.swap23 := kind === 1.U
    in.typeTagIn := index.U
    in.typeTagOut := index.U
    in.fmaCmd := op
    in.rm := rm
    in.in1 := t.recode(a(t.ieeeWidth - 1, 0))
    in.in2 := t.recode(b(t.ieeeWidth - 1, 0))
    in.in3 := t.recode(c(t.ieeeWidth - 1, 0))
    in
  }
  val refs = types.zipWithIndex.map { case (t, index) =>
    val latency = if (t == FType.D) 6 else 5
    val unit = Module(new FPUFMAPipe(latency, t))
    unit.io.in.valid := valid && tag === index.U
    unit.io.in.bits := inputs(index)
    Pipe(unit.io.out, 6 - latency)
  }
  val shared = Module(new FPUSharedFMAPipe(6))
  shared.io.in.valid := valid
  shared.io.in.bits := VecInit(inputs)(tag)
  val outputTag = Pipe(valid, tag, 6)
  val originalData = VecInit(types.zip(refs).map { case (t, r) => t.ieee(r.bits.data(t.recodedWidth - 1, 0)).pad(64) })
  val sharedData = VecInit(types.map(t => t.ieee(shared.io.out.bits.data(t.recodedWidth - 1, 0)).pad(64)))
  expected := originalData(outputTag.bits)
  actual := sharedData(outputTag.bits)
  expectedFlags := VecInit(refs.map(_.bits.exc))(outputTag.bits)
  actualFlags := shared.io.out.bits.exc
  outValid := shared.io.out.valid
  equal := shared.io.out.valid === outputTag.valid &&
    (!outputTag.valid || (expected === actual && expectedFlags === actualFlags))
}

object EmitFmaChecks extends App {
  val base: Parameters = new ToyLinux8x8Config().toInstance
  val tile = base(TilesLocated(InSubsystem)).collect {
    case attachment: BBTileAttachParams => attachment.tileParams
  }.head
  implicit val p: Parameters = base.alterPartial {
    case TileKey => tile.copy(core = tile.rocketCorePerCore.head)
  }
  ChiselStage.emitSystemVerilogFile(new FmaPrecisionCheck,
    Array("--target-dir", "build/fma-check"),
    Array("-disable-all-randomization", "-strip-debug-info"))
}
