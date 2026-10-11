package fpga.arty.linux

import java.nio.file.{Files, Paths}
import org.chipsalliance.cde.config.{Config, Field}
import freechips.rocketchip.rocket.RocketCoreParams
import freechips.rocketchip.tile.FpgaSharedFma
import freechips.rocketchip.devices.debug.DebugModuleKey
import freechips.rocketchip.devices.tilelink.{BootROMLocated, BootROMParams}
import freechips.rocketchip.subsystem._
import freechips.rocketchip.util.SystemFileName
import framework.system.core.rocket.configs.RocketCpuParam
import framework.system.tile.{BBTileAttachParams, WithBBTile}
import framework.top.GlobalConfig

case object TrimOptionalPeripherals extends Field[Boolean](false)
case object CompactCaches extends Field[Boolean](false)
case object SerialFpga extends Field[Boolean](false)
case object GemminiOnlyBalls extends Field[Boolean](false)

object OriginalToy {
  private val json = ujson.read(Files.readString(Paths.get("build/original-toy.json")))
  val cpu = upickle.default.read[RocketCpuParam](json("cpu"))
  private val original = upickle.default.read[GlobalConfig](json("accelerator"))
  val accelerator = original.copy(ballDomain = original.ballDomain.copy(
    ballIdMappings = original.ballDomain.ballIdMappings.map { mapping =>
      mapping.copy(config = mapping.config.map(path => Paths.get("upstream", path).toAbsolutePath.toString))
    }
  ))
  require(cpu.useVM && cpu.fpu.enable && cpu.useZba && cpu.useZbb && cpu.useZbs)
  require(accelerator.ballDomain.ballNum == 4)
  val gemminiOnly = accelerator.copy(
    ballDomain = accelerator.ballDomain.copy(
      ballNum = 1,
      ballIdMappings = accelerator.ballDomain.ballIdMappings.filter(_.ballId == 0),
      ballISA = accelerator.ballDomain.ballISA.filter(_.bid == 0)
    ),
    // Only the removed MXFP converter consumes this private scale-byte pool.
    // This is unrelated to the CPU's external MMIO/peripheral AXI port.
    memDomain = accelerator.memDomain.copy(mmioEnable = false)
  )
  require(gemminiOnly.ballDomain.ballIdMappings.map(_.ballName) == Seq("GemminiBall"))
  require(gemminiOnly.ballDomain.ballIdMappings.forall(m => m.mmioReadBW == 0 && m.mmioWriteBW == 0))
  // Keep all 23 Gemmini instructions and the 8x8 arithmetic profile.
  // Eight physical banks hold 64 KiB; architectural virtual IDs stay 0..15.
  val serial = gemminiOnly.copy(
    ballDomain = gemminiOnly.ballDomain.copy(
      ballIdMappings = gemminiOnly.ballDomain.ballIdMappings.map(mapping =>
        mapping.copy(config = Some(Paths.get("config/gemmini-8.toml").toAbsolutePath.toString)))),
    frontend = gemminiOnly.frontend.copy(sub_rob_depth = 8),
    memDomain = gemminiOnly.memDomain.copy(
      bankNum = 8, bankWidth = 64, bankMaskLen = 8, dma_buswidth = 64, dma_n_xacts = 2, max_in_flight_mem_reqs = 4,
      tmaReadChannel = 1, tmaWriteChannel = 1)
  )
  require(serial.memDomain.bankChannel == 7)
}

class WithArtyLinuxPorts extends Config((site, here, up) => {
  case FpgaSharedFma => true
  case ExtMem => Some(MemoryPortParams(
    master = MasterPortParams(BigInt("80000000", 16), BigInt(256) * 1024 * 1024, 16, 4, 64),
    nMemoryChannels = 1
  ))
  // Reserve the original SCU address range for the physical peripheral bridge.
  case ExtBus => Some(MasterPortParams(BigInt("60000000", 16), BigInt("10000000", 16), 8, 2, 8))
  case ExtIn => None
  case DebugModuleKey => None
  case BootROMLocated(InSubsystem) => Seq(BootROMParams(
    hang = BigInt("10000", 16),
    appendDTB = true,
    contentFileName = SystemFileName("upstream/arch/src/main/resources/bootrom/linux/bootrom.rv64.img")
  ))
  case SystemBusKey => up(SystemBusKey, site).copy(beatBytes = 16, dtsFrequency = Some(BigInt(50000000)))
  case MemoryBusKey => up(MemoryBusKey, site).copy(beatBytes = 16, dtsFrequency = Some(BigInt(50000000)))
  case PeripheryBusKey => up(PeripheryBusKey, site).copy(dtsFrequency = Some(BigInt(50000000)))
  case ControlBusKey => up(ControlBusKey, site).copy(dtsFrequency = Some(BigInt(50000000)))
  case FrontBusKey => up(FrontBusKey, site).copy(dtsFrequency = Some(BigInt(50000000)))
  // FPGA clock enables replace ASIC clock gates; execution features stay intact.
  case TilesLocated(InSubsystem) => up(TilesLocated(InSubsystem), site).map {
    case attachment: BBTileAttachParams =>
      val tile = attachment.tileParams
      attachment.copy(tileParams = tile.copy(
        core = tile.core.copy(clockGate = false, haveSimTimeout = false,
          fpu = tile.core.fpu.map(f => f.copy(sfmaLatency = f.dfmaLatency))),
        rocketCorePerCore = tile.rocketCorePerCore.map(c => c.copy(clockGate = false, haveSimTimeout = false,
          fpu = c.fpu.map(f => f.copy(sfmaLatency = f.dfmaLatency)))),
        dcache = tile.dcache.map(_.copy(clockGate = false))
      ))
    case other => other
  }
})

class ToyLinuxConfig(accelerator: GlobalConfig = OriginalToy.accelerator, withL2: Boolean = true) extends Config(
  new WithArtyLinuxPorts ++
    new WithBBTile(
      tileParam = accelerator.tile,
      buckyballConfig = accelerator,
      rocketCpuPerCore = Some(Seq(OriginalToy.cpu))
    ) ++
    new WithNExtTopInterrupts(1) ++
    new WithDTS("ucb-bar,buckyball", Nil) ++
    (if (withL2) new WithInclusiveCache(capacityKB = 64) else new Config((site, here, up) => PartialFunction.empty)) ++
    new WithCoherentBusTopology ++
    new freechips.rocketchip.system.BaseConfig
)

// Remove optional debug facilities and unused auxiliary RAM only.
// Linux privilege levels, MMU, FPU, caches and architectural counters stay intact.
class WithTrimOptionalPeripherals extends Config((site, here, up) => {
  case TrimOptionalPeripherals => true
  case TilesLocated(InSubsystem) =>
    def trim(core: RocketCoreParams): RocketCoreParams = {
      require(core.nPerfCounters == 0, "The baseline already has no extra HPM counters")
      require(core.haveBasicCounters && core.useVM && core.fpu.nonEmpty)
      core.copy(useDebug = false, nBreakpoints = 0, useBPWatch = false)
    }
    up(TilesLocated(InSubsystem), site).map {
      case attachment: BBTileAttachParams =>
        val tile = attachment.tileParams
        attachment.copy(tileParams = tile.copy(
          core = trim(tile.core),
          rocketCorePerCore = tile.rocketCorePerCore.map(trim)
        ))
      case other => other
    }
})

class ToyLinuxTrimmedConfig extends Config(
  new WithTrimOptionalPeripherals ++ new ToyLinuxConfig
)

// Capacity and speculation tradeoffs only; keep the ISA and coherence protocol.
class WithCompactCaches extends Config((site, here, up) => {
  case CompactCaches => true
  case InclusiveCacheKey =>
    val cache = up(InclusiveCacheKey, site)
    require(cache.ways == 8 && cache.sets == 128)
    cache.copy(ways = 4) // 128 sets * 4 ways * 64 bytes = 32 KiB.
  case TilesLocated(InSubsystem) => up(TilesLocated(InSubsystem), site).map {
    case attachment: BBTileAttachParams =>
      val tile = attachment.tileParams
      attachment.copy(tileParams = tile.copy(
        btb = None,
        icache = tile.icache.map(_.copy(nWays = 2)), // 64 sets, 8 KiB.
        dcache = tile.dcache.map(_.copy(nMSHRs = 1)) // Capacity stays 8 KiB.
      ))
    case other => other
  }
})

class ToyLinuxCompactConfig extends Config(
  new WithCompactCaches ++ new ToyLinuxTrimmedConfig
)

class WithGemminiOnlyMarker extends Config((site, here, up) => {
  case GemminiOnlyBalls => true
})

class ToyLinuxGemminiOnlyConfig extends Config(
  new WithGemminiOnlyMarker ++ new WithCompactCaches ++
    new WithTrimOptionalPeripherals ++ new ToyLinuxConfig(OriginalToy.gemminiOnly)
)


// Broadcast coherence still probes dirty CPU cache lines for accelerator DMA.
// It replaces the inclusive data cache, not the coherence protocol.
class WithSerialFpga extends Config((site, here, up) => {
  case SerialFpga => true
  case GemminiOnlyBalls => true
  case CompactCaches => true
  case BroadcastKey => up(BroadcastKey).copy(nTrackers = 2)
  case TilesLocated(InSubsystem) => up(TilesLocated(InSubsystem), site).map {
    case attachment: BBTileAttachParams =>
      val tile = attachment.tileParams
      attachment.copy(tileParams = tile.copy(
        btb = None,
        icache = tile.icache.map(_.copy(nWays = 2)),
        dcache = tile.dcache.map(_.copy(nMSHRs = 1))
      ))
    case other => other
  }
})

class ToyLinux8x8Config extends Config(
  new WithSerialFpga ++ new WithTrimOptionalPeripherals ++
    new ToyLinuxConfig(OriginalToy.serial, withL2 = false)
)
