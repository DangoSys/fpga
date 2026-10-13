# ROB/PR10 工程预发布下载

目标为 **Digilent Arty A7-100T / XC7A100T-CSG324-1**。本版合并 ROB 操作数 BRAM 优化
和 PR10 修复，保持 CPU、Sv39、FP16/32/64、Gemmini 8×8 及既有接口。
通过完整实现和 RTL 回归；发布时未连接板卡。后续队友报告本版实板通过，
原始实板日志待补，见 [回传说明](evidence/2026-10-13/team-return/README.md)。
资源、原文报告、测试与已知 MMIO 限制见 [完整报告](evidence/2026-10-13/rob-pr10-full/REPORT.md)。

[GitHub 工程预发布](https://github.com/DangoSys/fpga/releases/tag/arty-a7-rob-pr10-2026-10-13)
提供以下文件；旧 2026-10-12 的 UART/Flash 附件保持原值。

| 文件 | 用途 |
|---|---|
| [UART 完整包](https://github.com/DangoSys/fpga/releases/download/arty-a7-rob-pr10-2026-10-13/arty-a7-rob-pr10-uart.zip) | 位流、配套软件、Tcl、板级/生成 RTL、中文说明和一键加载/测试入口 |
| [源码包](https://github.com/DangoSys/fpga/releases/download/arty-a7-rob-pr10-2026-10-13/arty-a7-rob-pr10-sources.zip) | 仓库快照、实际生成 RTL、原 FPU 基线、软件依赖源码/配置、许可证和验证证据 |
| [位流](https://github.com/DangoSys/fpga/releases/download/arty-a7-rob-pr10-2026-10-13/toy_a7_rob_pr10_uart.bit) | 单独临时 JTAG 配置；仍需加载软件到 DDR |
| [烧录 Tcl](https://github.com/DangoSys/fpga/releases/download/arty-a7-rob-pr10-2026-10-13/program_arty.tcl) | 原生异常和 DONE/EOS/CRC 检查，可从任意目录调用 |
| [实现 Tcl](https://github.com/DangoSys/fpga/releases/download/arty-a7-rob-pr10-2026-10-13/build_board.tcl) | 配合完整包的 board/ 和生成 RTL 重建，不是单文件构建环境 |

位流 SHA256 为 `9f6f684361c049527fda09818cc8aa464f1067b75f3762305a27c5c738295942`。
下载后用 Release 的 SHA256SUMS.txt 检查附件，ZIP 内 verify_bundle.py 检查全部内容。
RELEASE_MANIFEST.json 同时记录发布源码提交与实际验证输入提交，测试/文档追加不伪装成重新构建。

Windows 解压完整包后，按真实路径执行：

已克隆仓库的队友可以直接使用仓库的 `run_hardware.ps1` 自动下载并验证这个固定版本，
无需手动解压；见[仓库实板入口](HARDWARE_TEST.md)。下面的 `run_uart.ps1` 仍适用于已解压包。

```powershell
.\run_uart.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

入口读取包内的新位流摘要，不沿用旧位流的默认值。临时 JTAG→软件完整 DDR 读回→Linux/
Gemmini 测试，日志留在新 build/ 目录。仅用 Hardware Manager 即可烧录；重建需要 Artix-7
器件支持。本包不是 Flash 固化包，掉电后须重载，不能替换旧 Flash 包的配套 MCS。
