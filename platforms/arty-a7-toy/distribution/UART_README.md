# Arty A7-100T：临时加载 Linux/Gemmini

本包包含已在实物验证的 `toy_a7_uart.bit`、最新 `fw_payload.bin`、软件构建记录、
烧录 Tcl、串口运行器及对应证据。无需重新综合或交叉编译。

目标为 **Digilent Arty A7-100T / xc7a100tcsg324-1**。CPU 25 MHz、DDR 256 MiB、
Gemmini 8×8，串口 1 Mbps、8N1。采用官方 E.0 MIG；实测板的 PCB 修订号未知，
不能认定其他 PCB 修订号或其他 A7 板也已验证。此包是工程验证版本。

## Windows 操作

1. 使用数据 USB 线连接板上 **PROG/UART**，SW0=0，关闭其他串口客户端。
2. 安装 Vivado/Hardware Manager 与 Digilent/FTDI 驱动；Python 3.10+。
   本次使用 Vivado 2025.1；本机烧录无需重新安装 Artix 综合组件。
   FTDI D2XX 入口需要 `C:/Windows/System32/ftd2xx.dll`。
3. 在解压目录打开 PowerShell，替换实际串口和 Vivado 路径：

```powershell
python -m pip install -r requirements.txt
python verify_bundle.py
.\run_uart.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

脚本先核验所有文件摘要，临时配置 FPGA，完整写入并读回 25,797,640 字节，
启动 OpenSBI/Linux，再执行 15 个程序。总超时一小时；程序侧另有超时保护。
本次完整传输/读回约 806 秒，复用已加载镜像的回归约 124 秒，均不是纯计算耗时。
日志及结果保存在解压目录的 `build/hardware-gemmini-*/`。

通过条件包括 `PASS FULL_DDR_READBACK`、`PASS LINUX_BOOT`、五项 Linux 检查、
`PASS GEMMINI_LINUX_CHECK cases=16`，以及原 13 项 Gemmini 测试返回 0。
如需完整独立核验，运行：

```powershell
python scripts/verify_linux_gemmini.py --build-record LINUX_GEMMINI_BUILD.json --hardware-result build/hardware-gemmini-实际目录/RESULT.json
```

## 断电行为与范围

本流程不改 Flash。配置和 DDR 软件在断电后丢失；此前 Flash 有镜像时，会回到
那个固化版本。单独 JTAG 下载 `.bit` 只配置硬件，仍须把软件加载到 DDR。

已验证系统启动、CPU/虚存/FP64 检查和本包矩阵用例；尚未验证完整模型、全面
浮点异常/舍入和长期稳定性。跨 K 分块由 CPU 累加，小矩阵不保证比 CPU 快。

源码、构建输入和原许可证见同一 Release 的 `arty-a7-toy-sources.zip`。
本包 `notices/` 保留硬件依赖声明；Linux、BusyBox、OpenSBI 和其他组件遵循各自许可证。
