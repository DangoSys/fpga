package fpga.arty.linux

import java.nio.file.{Files, Paths}
import org.chipsalliance.cde.config.Config
import freechips.rocketchip.devices.debug.DebugModuleKey
import freechips.rocketchip.devices.tilelink.{BootROMLocated, BootROMParams}
import freechips.rocketchip.subsystem._
import freechips.rocketchip.util.SystemFileName
import framework.system.core.rocket.configs.RocketCpuParam
import framework.system.tile.{BBTileAttachParams, WithBBTile}
import framework.top.GlobalConfig

object OriginalPebble {
  private val json = ujson.read(Files.readString(Paths.get("build/original-pebble.json")))
  val cpu = upickle.default.read[RocketCpuParam](json("cpu"))
  private val original = upickle.default.read[GlobalConfig](json("accelerator"))
  val accelerator = original.copy(ballDomain = original.ballDomain.copy(
    ballIdMappings = original.ballDomain.ballIdMappings.map { mapping =>
      mapping.copy(config = mapping.config.map(path => Paths.get("upstream", path).toAbsolutePath.toString))
    }
  ))
  require(cpu.useVM && cpu.fpu.enable && cpu.useZba && cpu.useZbb && cpu.useZbs)
  require(accelerator.ballDomain.ballNum == 10)
}

class WithArtyLinuxPorts extends Config((site, here, up) => {
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
        core = tile.core.copy(clockGate = false, haveSimTimeout = false),
        rocketCorePerCore = tile.rocketCorePerCore.map(_.copy(clockGate = false, haveSimTimeout = false)),
        dcache = tile.dcache.map(_.copy(clockGate = false))
      ))
    case other => other
  }
})

class PebbleLinuxConfig extends Config(
  new WithArtyLinuxPorts ++
    new WithBBTile(
      tileParam = OriginalPebble.accelerator.tile,
      buckyballConfig = OriginalPebble.accelerator,
      rocketCpuPerCore = Some(Seq(OriginalPebble.cpu))
    ) ++
    new WithNExtTopInterrupts(1) ++
    new WithDTS("ucb-bar,buckyball", Nil) ++
    new WithInclusiveCache() ++
    new WithCoherentBusTopology ++
    new freechips.rocketchip.system.BaseConfig
)
