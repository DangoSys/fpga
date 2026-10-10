package fpga.arty.linux

import java.nio.file.{Files, Paths}
import chisel3._
import circt.stage.ChiselStage
import org.chipsalliance.cde.config.Parameters
import org.chipsalliance.diplomacy.lazymodule.LazyModule
import freechips.rocketchip.diplomacy.{AddressSet, BufferParams}
import freechips.rocketchip.system.ExampleRocketSystem
import freechips.rocketchip.subsystem.MBUS
import freechips.rocketchip.tilelink.{TLBuffer, TLFragmenter, TLRAM}
import freechips.rocketchip.resources.{Description, MemoryDevice, ResourceBindings, ResourceString}
import freechips.rocketchip.util.ElaborationArtefacts

class PebbleLinuxSystem(implicit p: Parameters) extends ExampleRocketSystem {
  // Same capacity/address/bus as BuckyballBaseConfig's WithMbusScratchpad.
  private val bus = locateTLBusWrapper(MBUS)
  private val scratchDevice = new MemoryDevice {
    override def describe(resources: ResourceBindings): Description = {
      val original = super.describe(resources)
      original.copy(mapping = original.mapping + ("status" -> Seq(ResourceString("disabled"))))
    }
  }
  val scratchpad = bus {
    LazyModule(new TLRAM(AddressSet(BigInt("08000000", 16), 65535),
      beatBytes = bus.beatBytes, devOverride = Some(scratchDevice)))
  }
  bus.coupleTo("pebble-scratchpad") {
    scratchpad.node := TLFragmenter(bus.beatBytes, bus.blockBytes) :=
      TLBuffer(BufferParams.default) := TLBuffer(BufferParams.default) := _
  }
}

// Complete CPU/cache/accelerator resource boundary. External AXI ports must
// terminate in real DDR and peripherals before this becomes a board design.
class PebbleLinuxChip(implicit p: Parameters) extends Module {
  val system = LazyModule(new PebbleLinuxSystem)
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

object EmitPebbleLinux extends App {
  implicit val parameters: Parameters = new PebbleLinuxConfig().toInstance
  val directory = args.headOption.getOrElse("generated")
  // Use CIRCT's memory-macro boundary for a board-specific SRAM implementation.
  // The CPU and operator Chisel sources remain unchanged.
  val memoryOptions = if (args.drop(1).contains("--fpga-memories")) {
    Array("--repl-seq-mem", s"--repl-seq-mem-file=$directory/memories.conf")
  } else Array.empty[String]
  ChiselStage.emitSystemVerilogFile(
    new PebbleLinuxChip,
    args = Array("--target-dir", directory),
    firtoolOpts = Array("-disable-all-randomization", "-strip-debug-info") ++ memoryOptions
  )
  ElaborationArtefacts.files.foreach { case (name, content) =>
    Files.writeString(Paths.get(directory, s"PebbleLinuxChip.$name"), content())
  }
}
