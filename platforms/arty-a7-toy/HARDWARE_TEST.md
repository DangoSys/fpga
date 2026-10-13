# 从仓库直接运行实板验证

目标：**Digilent Arty A7-100T / XC7A100T-CSG324-1**。入口固定到
`HARDWARE_RELEASE.json` 中的 ROB/PR10 UART 工程预发布，自动下载约 9.7 MB 的运行包，
核对 ZIP、清单、位流和软件摘要，再复用原 `host/check_linux_gemmini.py` 与烧录 Tcl。
无需重新编译硬件、构建 Linux、拉取子模块或登录研究服务器。
该位流通过实现和 RTL 验证，队友已回传本版实板通过的报告，原始日志待补；
见 [回传说明](evidence/2026-10-13/team-return/README.md)。旧阶段见 [history/](../../history/README.md)。

## 首次准备

使用 Windows、64 位 Python 3.10+、Vivado Hardware Manager 与 Digilent/FTDI 驱动。
仅下载和烧录不要求安装 Artix-7 综合器件包。本次目录整理单独位于
`codex/organize-history` 分支；尚未合并时先在仓库根目录取得该分支，再进入平台目录：

```powershell
git fetch origin codex/organize-history
git switch --detach FETCH_HEAD
cd platforms/arty-a7-toy
python -m pip install -r host/requirements-hardware.txt
```

连接板卡 **PROG/UART USB**，保持 **SW0=0**，关闭其他串口工具。设备管理器中的
USB Serial Port 对应 FT2232 的 **UART B**；请按实际端口修改 `COM5`。
驱动应提供 `C:\Windows\System32\ftd2xx.dll`。默认速率为 1,000,000，8N1。
PCB 修订号仍未确认，当前 DDR 使用官方 Rev E 参数；其他板卡不在这个入口的适用范围。

## 一条命令加载并验证

```powershell
.\run_hardware.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

Python 不在 PATH 时加 `-Python 'D:\python\python.exe'`。可以从任意工作目录以完整路径
调用脚本，包含空格的路径需加引号。入口先检查驱动、串口和 Vivado 路径，再配置 FPGA、
将约 25.8 MB 软件加载到 DDR 并完整读回、启动 Linux、执行 15 个程序。
覆盖五项 Linux 系统检查、原 13 项 Gemmini 测试及 16 项 OS/WS 矩阵对照。
DDR 传输与读回需要数分钟，进度直接显示，实板验证总超时一小时。

成功必须出现 `PASS_LINUX_AND_GEMMINI_HARDWARE`，15 个程序均返回 0，DDR 读回长度、
位流与镜像摘要一致。失败或超时返回非零；不复用旧 PASS，不把离线准备标成实板通过。

## 离线准备 / GitHub 下载不通

没有接板时，只准备文件：

```powershell
.\run_hardware.ps1 -PrepareOnly
```

它不访问串口、不调用 Vivado，结果为 `PREPARED_NOT_HARDWARE_TESTED`。
若自动下载失败，从[固定 Release](https://github.com/DangoSys/fpga/releases/tag/arty-a7-rob-pr10-2026-10-13)
下载 `arty-a7-rob-pr10-uart.zip`，无需手动解压，再执行：

```powershell
.\run_hardware.ps1 -PrepareOnly -BundleZip 'D:\Downloads\arty-a7-rob-pr10-uart.zip'
# 接板后仍可指定这个 ZIP，或者直接运行前面的一条命令，入口会复用已校验缓存。
```

缓存位于 `build/hardware-release/<tag>/`。每次复用均重新校验，摘要错误会终止，
请勿编辑缓存中的源码、清单或镜像；切换版本需更新固定发布信息并重新验证。

## 给队友检查的日志

每次入口记录独立写入 `build/hardware-entry/<时间-随机标识>/RUN.json`，包含发布版本、
摘要、状态以及本次原验证器 `RESULT.json` 的路径。
原始编程日志、Linux 串口输出和每个程序的退出码位于
`build/hardware-release/<tag>/bundle/build/hardware-gemmini-<日期-随机标识>/`。
分享本轮目录及入口记录即可；历史测试日志不覆盖。

此流程临时修改 FPGA SRAM 与 DDR，**不擦写 Flash**。掉电后需要重跑；它与已发布的
Flash 冷启动流程分别使用对应产物。完整能力和 MMIO 同步异常限制见
[完整验证报告](evidence/2026-10-13/rob-pr10-full/REPORT.md)。
