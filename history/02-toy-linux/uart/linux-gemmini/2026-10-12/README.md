# Linux/Gemmini 实物测试归档索引

[报告](REPORT.md)给出范围和计时；[复现指南](../../../software/GEMMINI_LINUX.md)
包含软件镜像构建、FPGA 位流来源、主机依赖、实物命令和离线核验。
本目录保存有用的测试信息，不包含与板子功能无关的排查记录。

| 路径 | 内容与来源 |
|---|---|
| `build/` | 完整软件构建日志、固定依赖/配置、rootfs 安装核验和镜像摘要 |
| `generated-inputs/` | 实际编译的 14 个 Gemmini C 程序、参数、23 个 opcode 定义及 CMake |
| `load/` | 完整 DDR 写入/读回进度、Linux 启动阶段原文前缀及派生阶段记录 |
| `hardware/` | 最终回归完整串口、15 个程序摘要/返回码、16 项计时、JTAG 日志、最终 shell 检查 |
| `first-pass/` | 前一次通过回归的完整算子日志/结果/计时，保留重复运行证据 |
| `watchdog/` | 正常/非零退出、刻意超时及 watcher 回收检查，137 属于预期结果 |
| `sources/` | 实际执行版本的构建/测试脚本、新测试 C、UART loader、`program.tcl` 和 `board/program_arty.tcl` |

原 13 个参考 C 源码、ISA/DMA 库在平台 `tests/reference/`，由
`tests/REFERENCE_MANIFEST.json` 固定至 Buckyball `1f3d545`；原 Linux 检查源码为
`software/linux_system_check.c`。`build/INPUT_MANIFEST.json` 绑定实际 47 个来源和
18 个生成输入；生成 C 与参考 C 的唯一尺寸适配是 `#define DIM 16` → `8`。

本次没有重新综合/布线，使用原已验证 UART 位流。其实现报告和输入 Tcl 在
`evidence/2026-10-11/`；本次实际烧录 Tcl 的原文快照位于 `sources/`。
当前便携入口相比快照补充日期命名、新位流摘要参数和 watchdog 调用接口。
上传器的 SSH 接入整理为仓库外 `connect(client)` 接口；归档中的上传器是对应的
公开接口副本，不标作逐字执行快照。构建/上传循环及实际编译输入保持不变。
历史实物结论只属于记录里的精确摘要，重新生成的产物必须重新验证。

Linux 构建工具为 GCC 15.3.0 / Binutils 2.46；主机为 Python 3.10.11、pyserial 3.5、
paramiko 5.0.0、Vivado 2025.1，D2XX DLL 产品版本 2.12.36.20。
板卡为 Arty A7-100T、CPU 25 MHz、CLINT 500 kHz、UART 1 Mbps 8N1。
PCB revision 未确认，沿用已在实物工作过的官方 E.0 MIG 参数。

`MANIFEST.json` 逐文件标注摘要/类型：回归日志为完整原文，加载/启动为明确选取的
阶段前缀，阶段 JSON 是派生摘要。离线校验会核对这些关系，不能将加载阶段摘要
当作其他阶段已通过。本轮未写 Flash；没有整模型、全 DDR、全面 FPU 或长期功耗验收。
