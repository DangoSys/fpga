# 已验证烧录文件下载

烧录产物通过 [GitHub Release：arty-a7-toy-2026-10-12](https://github.com/DangoSys/fpga/releases/tag/arty-a7-toy-2026-10-12)
提供；源码与测试证据仍保存在 Git。下载包自带配套软件、Tcl、中文操作说明和逐文件摘要，
无需重新运行 Chisel、Vivado 综合/布线或 Linux 编译。

仅面向 **Digilent Arty A7-100T / XC7A100T-CSG324-1**，Vivado part 为
`xc7a100tcsg324-1`。采用官方 E.0 MIG，实测 PCB 修订号未知；此 Release 标为
工程预发布，未完成整模型、全面浮点和长期稳定性验收。

## 选择下载包

| 文件 | 用途 | 软件与掉电行为 |
|---|---|---|
| [arty-a7-toy-uart.zip](https://github.com/DangoSys/fpga/releases/download/arty-a7-toy-2026-10-12/arty-a7-toy-uart.zip) | 联调、修改软件、复现最新测试 | 最新 Linux/Gemmini 镜像，完整 DDR 读回；掉电后需要重新加载 |
| [arty-a7-toy-flash.zip](https://github.com/DangoSys/fpga/releases/download/arty-a7-toy-2026-10-12/arty-a7-toy-flash.zip) | 固化演示、脱机运行 | 配套 MCS、旧标准 Linux 镜像；已通过实际断电重接与五项系统检查 |
| [arty-a7-toy-sources.zip](https://github.com/DangoSys/fpga/releases/download/arty-a7-toy-2026-10-12/arty-a7-toy-sources.zip) | 检查、修改与重新构建 | 仓库快照、固定软件依赖源码、实际配置、许可证与证据 |

Flash 包保留 CPU、虚拟内存、FPU 和 Gemmini 8×8，但其 rootfs **没有最新 14 个
Gemmini 测试程序**。最新用例验证结论对应 UART 包，不能据此认定 Flash 中已经有它们。
两个包均有 Linux，用途不同；不建议只下载 `.bit` 后省略配套软件。

## 直接下载位流

- [toy_a7_uart.bit](https://github.com/DangoSys/fpga/releases/download/arty-a7-toy-2026-10-12/toy_a7_uart.bit)：临时 JTAG 配置，需要串口加载 `fw_payload.bin` 到 DDR。
- [toy_a7_flash.bit](https://github.com/DangoSys/fpga/releases/download/arty-a7-toy-2026-10-12/toy_a7_flash.bit)：Flash 启动目标，需要配套压缩软件；固化时使用完整 Flash 包的 MCS。

Release 的 `SHA256SUMS.txt` 校验下载文件，`RELEASE_MANIFEST.json` 绑定源码提交和
各附件摘要；每个 ZIP 的 `MANIFEST.json` 再校验包内全部文件。
UART 位流 SHA256 为 `ccc33c511e613561fb9dd1e9c847bd3b84037da1d078c44cd3de197d55dffde1`；
Flash 位流为 `78d2e703372c13c5044674c8d4eea5b775d6b12771d21df37ba0f90617723c18`。

## 使用与复现

后续 ROB RAM 优化候选已完成独立实物复测，记录见
[新位流实物报告](evidence/2026-10-12/rob-ram-hardware/REPORT.md)。该候选摘要为
`dec8dcaea14b56db49ef8166d1605034695658f55f02dce73d4455fbc078ee5c`，源码在
[PR #11](https://github.com/DangoSys/fpga/pull/11)。此处追加验证资料；上述 Release
仍提供原摘要的 UART/Flash 文件，候选的 Flash 冷启动没有在本轮测试。

解压后按包内中文 `README.md` 执行 `run_uart.ps1` 或 `run_flash.ps1`，脚本先校验
产物再烧录。安装 Python/pyserial、Vivado Hardware Manager、Digilent/FTDI 驱动，
连接 PROG/UART；替换真实串口和 Vivado 路径。Flash 入口要求明确指定实际 Flash 条目，
先备份再擦写。记录均保存在解压目录的新 `build/` 子目录中。

打包源码在 `scripts/package_downloads.py`，输入为五个已归档摘要固定的二进制和
`--os-inputs` 目录，输出目录必须不存在。该入口不构建、不连接板卡，只打包已验证
产物。软件依赖归档需与实物构建日志 CACHE 摘要一致，目录结构与传入参数见脚本。
上板测试方法见 [Linux/Gemmini 指南](software/GEMMINI_LINUX.md)，
固化流程见 [Flash 指南](FLASH_BOOT.md)。
