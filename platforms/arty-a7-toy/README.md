# Arty A7-100T：当前 Toy/Linux 平台

当前选择 **ROB 操作数 BRAM + PR10 修复的 UART 集成版**，器件 `xc7a100tcsg324-1`，
发布 `arty-a7-rob-pr10-2026-10-13`，属于 [阶段 03](../../history/03-rob-pr10/README.md)。
最早无 Linux 的 A7 原型和旧 Toy 记录已分阶段移入 [history/](../../history/README.md)。

## 队友直接运行

Windows、64 位 Python 3.10+、Vivado Hardware Manager 和 FTDI 驱动，进入本目录执行：

```powershell
python -m pip install -r host/requirements-hardware.txt
.\run_hardware.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

替换真实串口/路径，连接 PROG/UART USB、SW0=0。入口核对固定版本，临时配置 FPGA、
完整读回 DDR 软件、启动 Linux、执行 15 个程序，一小时超时。无板先用 `-PrepareOnly`；
[详细指南](HARDWARE_TEST.md)说明 Git 获取、离线 ZIP 与日志位置。

## 两条启动路线

| 路线 | 可用内容 | 验证范围 |
|---|---|---|
| 当前 UART | ROB/PR10 位流 + 标准 Linux/Gemmini 镜像；[下载](ROB_PR10_DOWNLOADS.md) | 实现/RTL 通过；队友报告实板通过，原始实板日志待补 |
| 旧 Flash 恢复 | 阶段 02 Flash 专用位流/MCS与原系统镜像；[流程](FLASH_BOOT.md) | 旧版本烧写与真实断电启动通过，不代表当前 ROB/PR10 已固化验收 |

启动 ROM、位流与镜像组合各有版本。当前 UART 不擦写 Flash，不能直接替换旧 MCS。
发布时 `physical_hardware_tested=false` 保留当时状态；后续报告在
[team-return/](evidence/2026-10-13/team-return/README.md)单独记录。

## 系统与代码

- RV64 CPU、M/S/U、PMP、Sv39，8 KiB I/D cache；FP16/32/64 共享 FMA。
- Gemmini 8×8 OS/WS、64 个 PE DSP、64 KiB SRAM，保留 23 个 opcode。
- 256 MiB DDR3L；CPU 25 MHz、MIG UI 83.33 MHz、CLINT 500 kHz、UART 1 Mbps。
- 官方 Rev E MIG 参数；实物 PCB 修订号未知。其他 Balls、L2、BTB、debug 等不在此 FPGA 配置中。

`src/`、`patches/` 是当前 Chisel 配置/覆盖；`rtl/` 为存储器适配；`board/` 为 DDR/时钟/引脚/Tcl；
`boot/` 保留 Flash 支持；`software/`、`host/`、`tests/` 为镜像、主机与验证。
`evidence/` 保存当前证据；旧记录由 `scripts/history_paths.py` 按阶段索引读取。

## 重建与开发

需要 Linux/Nix、JDK 17、sbt、Scala 2.13.16、Chisel 6.7.0、firtool 1.62.1、RV64 工具链、
Verilator/Icarus 和带 Artix-7 支持的 Vivado 2024.1。生成当前 BRAM 候选：

```bash
bash scripts/elaborate_rob_candidate.sh --repository ../../thirdparty/buckyball
bash scripts/build_test_programs.sh
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/run_board_regression.py
python3 scripts/start_rob_board_build.py
```

`--repository` 可省略，由脚本获取固定输入。普通 `elaborate.sh` / `start_board_build.py`
仍用于寄存器 ROB/Flash 基线，不是当前 BRAM 发布配置。默认关闭 BRAM，候选入口显式开启。
检查独立输出的 `RUN.json`，只使用 `COMPLETED`、退出 0、生成位流并通过实现检查的结果。
软件见 [Linux/Gemmini](software/GEMMINI_LINUX.md)，配置/限制见 [ROB](ROB_RAM.md)、
[验证范围](VALIDATION.md)和[接口说明](REVIEW_FIXES.md)。重建后须重新取得摘要与验收结果。
