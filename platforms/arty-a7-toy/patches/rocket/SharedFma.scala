// SPDX-License-Identifier: BSD-3-Clause
package freechips.rocketchip.tile

import chisel3._
import chisel3.util._
import org.chipsalliance.cde.config.Parameters

/** One unrounded FP64 FMA datapath, with direct H/S/D final rounding. */
class SharedMulAddRecFNPipe(implicit p: Parameters) extends FPUModule {
  require(fLen == 64 && minFLen == 16)
  val io = IO(new Bundle {
    val validin = Input(Bool())
    val op = Input(UInt(2.W))
    val typeTag = Input(UInt(2.W))
    val a = Input(UInt(65.W))
    val b = Input(UInt(65.W))
    val c = Input(UInt(65.W))
    val roundingMode = Input(UInt(3.W))
    val out = Output(new FPResult)
    val validout = Output(Bool())
  })
  val pre = Module(new hardfloat.MulAddRecFNToRaw_preMul(11, 53))
  val post = Module(new hardfloat.MulAddRecFNToRaw_postMul(11, 53))
  pre.io.op := io.op
  pre.io.a := io.a
  pre.io.b := io.b
  pre.io.c := io.c

  // Retain the original four-stage raw FMA partition: align, multiply, add,
  // normalize. Full product bits and sticky information survive until rounding.
  val mulA = Pipe(io.validin, pre.io.mulAddA, 1)
  val mulB = Pipe(io.validin, pre.io.mulAddB, 1)
  val alignedC = Pipe(io.validin, pre.io.mulAddC, 1)
  val meta = Pipe(io.validin, pre.io.toPostMul, 1)
  val product = Pipe(meta.valid, mulA.bits * mulB.bits, 1)
  val delayedC = Pipe(meta.valid, alignedC.bits, 1)
  val delayedMeta = Pipe(meta.valid, meta.bits, 1)
  val sum = product.bits +& delayedC.bits
  post.io.fromPreMul := Pipe(delayedMeta.valid, delayedMeta.bits, 1).bits
  post.io.mulAddResult := Pipe(delayedMeta.valid, sum, 1).bits
  val rmPost = Pipe(io.validin, io.roundingMode, 3)
  post.io.roundingMode := rmPost.bits

  val raw = Pipe(rmPost.valid, post.io.rawOut, 1)
  val invalid = Pipe(rmPost.valid, post.io.invalidExc, 1)
  val rm = Pipe(io.validin, io.roundingMode, 4)
  val tag = Pipe(io.validin, io.typeTag, 4)
  val results = floatTypes.map { t =>
    // Do not round to FP64 and convert afterward: that would double-round.
    val round = Module(new hardfloat.RoundAnyRawFNToRecFN(11, 55, t.exp, t.sig, 0))
    round.io.in := raw.bits
    round.io.invalidExc := invalid.bits
    round.io.infiniteExc := false.B
    round.io.roundingMode := rm.bits
    round.io.detectTininess := hardfloat.consts.tininess_afterRounding
    val result = Wire(new FPResult)
    result.data := sanitizeNaN(round.io.out, t)
    result.exc := round.io.exceptionFlags
    result
  }
  io.out := VecInit(results)(tag.bits)
  io.validout := tag.valid
}

/** The Rocket core issues at most one FMA per cycle; all formats share it. */
class FPUSharedFMAPipe(val latency: Int)(implicit p: Parameters) extends FPUModule {
  require(latency >= 5)
  require(fLen == 64 && minFLen == 16)
  val io = IO(new Bundle {
    val in = Flipped(Valid(new FPInput))
    val out = Valid(new FPResult)
  })
  def widen(x: UInt): UInt = {
    VecInit(floatTypes.map(t => t.unsafeConvert(x(t.recodedWidth - 1, 0), maxType)))(io.in.bits.typeTagOut)
  }
  val a = widen(io.in.bits.in1)
  val b = widen(io.in.bits.in2)
  val c = widen(io.in.bits.in3)
  val valid = RegNext(io.in.valid, false.B)
  val in = Reg(new FPInput)
  when (io.in.valid) {
    in := io.in.bits
    in.in1 := a
    in.in2 := Mux(io.in.bits.swap23, (BigInt(1) << 63).U(65.W), b)
    val zero = (a ^ b) & (BigInt(1) << 64).U(65.W)
    in.in3 := Mux(io.in.bits.ren3 || io.in.bits.swap23, c, zero)
  }
  val fma = Module(new SharedMulAddRecFNPipe)
  fma.io.validin := valid
  fma.io.op := in.fmaCmd
  fma.io.typeTag := in.typeTagOut
  fma.io.a := in.in1
  fma.io.b := in.in2
  fma.io.c := in.in3
  fma.io.roundingMode := in.rm
  io.out := Pipe(fma.io.validout, fma.io.out, latency - 5)
}
