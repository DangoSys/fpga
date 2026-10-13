# 当前 ROB 存储配置

当前 UART 发布显式启用 ROB 操作数 BRAM，保留 CPU、Sv39、FPU、Gemmini 8×8 和软件 ABI。
默认 Chisel 保留寄存器路径，供基线/等价比较。

用 `bash scripts/elaborate_rob_candidate.sh` 生成候选，
再用 `python3 scripts/start_rob_board_build.py` 完整实现，单次一小时超时。
普通 `elaborate.sh` / `start_board_build.py` 走寄存器配置，不是当前发布 profile。
相对 UART 基线减少 484 LUT、1,657 FF、84 Slice，增加 2 BRAM，DSP 不变；仅余 271 Slice。

旧候选 `dec8dcae…8ee5c` 尚无 PR10 修复，归入 [阶段 03](../../history/03-rob-pr10/README.md)，
原说明在 [文档快照](../../history/03-rob-pr10/uart/docs/ROB_RAM.md)。
当前 `9f6f6843…95942` 使用 [固定发布](ROB_PR10_DOWNLOADS.md)和 [队友入口](HARDWARE_TEST.md)，
[完整验证](evidence/2026-10-13/rob-pr10-full/REPORT.md)绑定重新生成/实现与 RTL 回归。
当前 ROB/PR10 尚无新版 Flash 冷启动资格。
