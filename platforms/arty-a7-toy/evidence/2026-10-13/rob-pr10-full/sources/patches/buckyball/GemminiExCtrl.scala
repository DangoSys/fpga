package examples.balls.gemmini

import chisel3._
import chisel3.util._
import chisel3.experimental.hierarchy.{instantiable, public}
import framework.top.GlobalConfig

@instantiable
class GemminiExCtrl(val b: GlobalConfig)
    extends Module
    with GemminiExCtrlDefs
    with GemminiExCtrlDefaults
    with GemminiExCtrlCmdStates
    with GemminiExCtrlPreloadStates
    with GemminiExCtrlComputeReadState
    with GemminiExCtrlComputeFeedState
    with GemminiExCtrlStoreOps
    with GemminiExCtrlFsm {
  @public val exio = io

  applyDefaults()
  runFsm()

  // WS output is associated with the preceding non-flush mesh request.
  // Unlike a ROB ID, the internal token changes for each loop iteration.
  when(mesh.io.req.fire && mesh.io.req.bits.flush === 0.U) {
    wsResultTag := lastMeshTag
    lastMeshTag := mesh.io.req.bits.tag.rob
    nextMeshTag := Mux(nextMeshTag === 254.U, 0.U, nextMeshTag + 1.U)
  }

  io.status.idle    := state === sIdle
  io.status.running := state =/= sIdle
}
