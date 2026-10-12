# Arty A7-100T：Flash 固化与断电启动

本包包含已通过实际断电重接验证的 `toy_a7_flash.bit`、配套 `toy_flash.mcs`、
压缩软件、校验记录和烧写脚本。MCS 已包含 FPGA 配置及 Linux 启动镜像，
无需在每次上电时连接电脑传输软件。

**这是先前固化验证的软件版本：含五项 Linux 系统检查，不含最新 14 个 Gemmini
测试程序。** 最新测试镜像在临时加载包中；不能把它与本包配套摘要混用。
CPU/Sv39/FPU/Gemmini 8×8 均保留。

目标仅为 **Digilent Arty A7-100T / xc7a100tcsg324-1**。使用官方 E.0 MIG，
实测 PCB 修订号未知。本次 Flash 为 S25FL128S、JEDEC `012018`，
配置存储器条目 `s25fl128sxxxxxx0-spi-x1_x2_x4`。其他板须先识别实际 Flash。

## Windows 操作

1. PROG/UART 接数据 USB 线，JP1/MODE 两针装跳线帽，SW0=0。
2. 安装 Vivado/Hardware Manager、Digilent/FTDI 驱动和 Python 3.10+；
   关闭其他串口客户端。本次使用 Vivado 2025.1。
3. 在解压目录执行，替换串口、工具路径及已确认的 Flash 条目：

```powershell
python -m pip install -r requirements.txt
python verify_bundle.py
.\run_flash.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat' -FlashPart s25fl128sxxxxxx0-spi-x1_x2_x4
```

脚本会备份全部 16 MiB 原内容到新的 `build/flash-program-*/flash-before.bin`，
然后擦写、校验 MCS，并要求从 Flash 重配置和进入 Linux。备份保持私有。
一小时总超时，保留全部烧写和启动日志；擦写/校验期间保持供电。

配置从 `0x000000` 开始，软件从 `0x400000` 开始。Boot ROM 从 Flash 读取、
解压并检查 CRC 后进入 DDR 中的 OpenSBI/Linux。此 `.bit` 必须配套软件，
只把 `.bit` 写进 Flash 不会完成软件固化。

## 冷启动核验与恢复

烧写成功后，先启动观察器：

```powershell
python host/observe_flash_boot.py --port COM5 --require-disconnect --transcript build/cold-boot.log --timeout 600
```

拔掉 USB 和其他所有供电，等至少 5 秒再接回。应出现 `PASS FLASH_PAYLOAD_CRC`、
OpenSBI/Linux，五项 Linux 检查均通过，返回 0。本次上电启动约两分钟。
需要临时加载软件时，可将 SW0=1 后按 BTN0，使用 UART 恢复入口。

本包已验证 Flash 烧写/读回、实际冷启动及五项系统检查；不继承临时包最新
Gemmini 测试的软件验收结论。完整模型、全面浮点测试和长期稳定性仍未验收。
证据见 `evidence/flash/`；源码与许可证见同一 Release 的 `arty-a7-toy-sources.zip`。
