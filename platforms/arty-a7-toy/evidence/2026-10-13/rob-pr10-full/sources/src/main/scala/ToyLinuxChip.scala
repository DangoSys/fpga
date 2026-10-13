package fpga.arty.linux

import java.nio.file.{Files, Paths}
import chisel3._
import circt.stage.ChiselStage
import org.chipsalliance.cde.config.Parameters
import org.chipsalliance.diplomacy.lazymodule.LazyModule
import freechips.rocketchip.diplomacy.{AddressSet, BufferParams}
import freechips.rocketchip.system.ExampleRocketSystem
import freechips.rocketchip.subsystem.{InSubsystem, InclusiveCacheKey, MBUS, TilesLocated}
import framework.system.tile.BBTileAttachParams
import freechips.rocketchip.tilelink.{TLBuffer, TLFragmenter, TLRAM}
import freechips.rocketchip.resources.{Description, MemoryDevice, ResourceBindings, ResourceString}
import freechips.rocketchip.util.ElaborationArtefacts

class ToyLinuxSystem(implicit p: Parameters) extends ExampleRocketSystem {
  // Optional auxiliary RAM. The Linux boot ROM jumps to DDR at 0x80000000;
  // it never uses this separate 0x08000000 region.
  if (!p(TrimOptionalPeripherals)) {
    val bus = locateTLBusWrapper(MBUS)
    val scratchDevice = new MemoryDevice {
      override def describe(resources: ResourceBindings): Description = {
        val original = super.describe(resources)
        original.copy(mapping = original.mapping + ("status" -> Seq(ResourceString("disabled"))))
      }
    }
    val scratchpad = bus {
      LazyModule(new TLRAM(AddressSet(BigInt("08000000", 16), 65535),
        beatBytes = bus.beatBytes, devOverride = Some(scratchDevice)))
    }
    bus.coupleTo("toy-scratchpad") {
      scratchpad.node := TLFragmenter(bus.beatBytes, bus.blockBytes) :=
        TLBuffer(BufferParams.default) := TLBuffer(BufferParams.default) := _
    }
  }
}

// Complete CPU/cache/accelerator resource boundary. External AXI ports must
// terminate in real DDR and peripherals before this becomes a board design.
class ToyLinuxChip(implicit p: Parameters) extends Module {
  val system = LazyModule(new ToyLinuxSystem)
  val core = Module(system.module)
  system.io_clocks.get.elements.values.foreach { domain =>
    domain.clock := clock
    domain.reset := reset.asBool
  }
  val interrupt = IO(Input(Bool()))
  core.interrupts := interrupt.asUInt
  require(system.mem_axi4.size == 1 && system.mmio_axi4.size == 1)
  val memory = IO(chiselTypeOf(system.mem_axi4.head))
  val peripherals = IO(chiselTypeOf(system.mmio_axi4.head))
  memory <> system.mem_axi4.head
  peripherals <> system.mmio_axi4.head
}

object EmitToyLinux extends App {
  val serial = args.drop(1).contains("--serial-fpga")
  val gemminiOnly = args.drop(1).contains("--gemmini-only")
  val compact = gemminiOnly || args.drop(1).contains("--compact-caches")
  val trimmed = compact || args.drop(1).contains("--trim-peripherals")
  implicit val parameters: Parameters =
    (if (serial) new ToyLinux8x8Config
     else if (gemminiOnly) new ToyLinuxGemminiOnlyConfig
     else if (compact) new ToyLinuxCompactConfig
     else if (trimmed) new ToyLinuxTrimmedConfig
     else new ToyLinuxConfig).toInstance
  val directory = args.headOption.getOrElse("generated")
  // Use CIRCT's memory-macro boundary for a board-specific SRAM implementation.
  // Original upstream sources stay intact; Gemmini arithmetic uses explicit overlays.
  val memoryOptions = if (args.drop(1).contains("--fpga-memories")) {
    Array("--repl-seq-mem", s"--repl-seq-mem-file=$directory/memories.conf")
  } else Array.empty[String]
  ChiselStage.emitSystemVerilogFile(
    new ToyLinuxChip,
    args = Array("--target-dir", directory),
    firtoolOpts = Array("-disable-all-randomization", "-strip-debug-info") ++ memoryOptions
  )
  ElaborationArtefacts.files.foreach { case (name, content) =>
    Files.writeString(Paths.get(directory, s"ToyLinuxChip.$name"), content())
  }
  val tiles = parameters(TilesLocated(InSubsystem)).collect {
    case attachment: BBTileAttachParams => attachment.tileParams
  }
  require(tiles.size == 1)
  val tile = tiles.head
  val core = tile.rocketCorePerCore.headOption.getOrElse(tile.core)
  val accelerator = tile.resolvedBuckyballPerCore.flatten.head
  val profile = ujson.Obj(
    "serial_fpga" -> parameters(SerialFpga),
    "gemmini_only_balls" -> parameters(GemminiOnlyBalls),
    "ball_count" -> accelerator.ballDomain.ballNum,
    "ball_names" -> ujson.Arr.from(accelerator.ballDomain.ballIdMappings.map(_.ballName)),
    "ball_ids" -> ujson.Arr.from(accelerator.ballDomain.ballIdMappings.map(_.ballId)),
    "ball_funct7" -> ujson.Arr.from(accelerator.ballDomain.ballISA.map(_.funct7)),
    "ball_read_ports" -> accelerator.ballDomain.ballIdMappings.map(_.inBW).sum,
    "ball_write_ports" -> accelerator.ballDomain.ballIdMappings.map(_.outBW).sum,
    "accelerator_mmio_scale_pool" -> accelerator.memDomain.mmioEnable,
    "compact_caches" -> parameters(CompactCaches),
    "btb_enabled" -> tile.btb.nonEmpty,
    "icache_bytes" -> (tile.icache.get.nSets * tile.icache.get.nWays * tile.icache.get.blockBytes),
    "icache_ways" -> tile.icache.get.nWays,
    "dcache_bytes" -> (tile.dcache.get.nSets * tile.dcache.get.nWays * tile.dcache.get.blockBytes),
    "dcache_mshrs" -> tile.dcache.get.nMSHRs,
    "l2_ways" -> (if (serial) 0 else parameters(InclusiveCacheKey).ways),
    "coherence_manager" -> (if (serial) "broadcast" else "inclusive"),
    "rob_entries" -> accelerator.frontend.rob_entries,
    "sub_rob_depth" -> accelerator.frontend.sub_rob_depth,
    "dma_n_xacts" -> accelerator.memDomain.dma_n_xacts,
    "dma_max_in_flight" -> accelerator.memDomain.max_in_flight_mem_reqs,
    "tma_read_channels" -> accelerator.memDomain.tmaReadChannel,
    "tma_write_channels" -> accelerator.memDomain.tmaWriteChannel,
    "cpu_mul_unroll" -> core.mulDiv.get.mulUnroll,
    "gemmini_rows" -> examples.balls.gemmini.configs.GemminiBallParam(accelerator).totalRows,
    "gemmini_columns" -> examples.balls.gemmini.configs.GemminiBallParam(accelerator).totalColumns,
    "virtual_bank_count" -> accelerator.memDomain.virtualBankCount,
    "trimmed_optional_peripherals" -> parameters(TrimOptionalPeripherals),
    "scratchpad_bytes" -> (if (parameters(TrimOptionalPeripherals)) 0 else 65536),
    "cpu_use_debug" -> core.useDebug,
    "cpu_breakpoints" -> core.nBreakpoints,
    "extra_hpm_counters" -> core.nPerfCounters,
    "basic_counters" -> core.haveBasicCounters,
    "use_vm" -> core.useVM,
    "fpu_shared_fma" -> parameters(freechips.rocketchip.tile.FpgaSharedFma),
    "fpu_sfma_latency" -> core.fpu.get.sfmaLatency,
    "fpu_dfma_latency" -> core.fpu.get.dfmaLatency,
    "fpu_min_flen" -> core.fpu.get.minFLen,
    "fpu_flen" -> core.fpu.get.fLen,
    "bank_count" -> accelerator.memDomain.bankNum,
    "bank_rows" -> accelerator.memDomain.bankEntries,
    "bank_width" -> accelerator.memDomain.bankWidth,
    "bank_channels" -> accelerator.memDomain.bankChannel
  )
  Files.writeString(Paths.get(directory, "ToyLinuxChip.profile.json"), ujson.write(profile, indent = 2))
}
