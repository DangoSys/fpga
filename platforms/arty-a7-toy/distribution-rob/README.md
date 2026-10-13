# Arty A7-100T：ROB 优化与 PR10 修复下载包

本包是 UART/JTAG 工程预发布，目标 **XC7A100T-CSG324-1**，CPU 25 MHz、UART 1 Mbps。
保留 RV64 CPU、Sv39、FP16/32/64、Gemmini 8×8，启用 ROB 操作数 BRAM，并包含 AXI
写错误响应修复。官方 E.0 MIG 参数保持原值；实际 PCB 修订号未知。

位流通过本轮综合、布局布线、时序、DRC/CDC 及 RTL 回归；软件采用此前已验证的
标准 Linux/Gemmini 镜像。**本轮没有连接实物板卡，未取得新位流实板或冷启动资格。**
具体数值、测试范围、源码提交和文件摘要见 `VALIDATION_RESULT.json` 与 `MANIFEST.json`。

非法 MMIO 检查确认 SLVERR 完整传到 CPU 的 AXI 输入，但当前非阻塞缓存在该用例中
未产生同步访问异常，不能把总线响应修复当作完整的物理总线错误保护。Linux 的虚拟内存
页面保护属于独立路径。整模型、长期 DDR 压力与环境稳定性也不在本次验收范围。

## 一键加载并测试（Windows）

安装 Python、`pip install pyserial==3.5`、Vivado Hardware Manager 及 Digilent/FTDI 驱动。
连接板卡 PROG/UART USB，SW0=0；确认串口是 USB UART 通道 B，然后执行：

```powershell
.\run_uart.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

请替换真实串口和 Vivado 路径。入口先核验包内摘要，再临时 JTAG 配置、完整 DDR 读回、
启动 Linux，执行 15 个程序。含五项 Linux 检查、13 项 Gemmini 测试和 16 项矩阵对照。
进度与日志写入本包 `build/`；软件传输及完整读回需要数分钟，测试设有超时。
程序启动后可通过同一 USB 串口以 1,000,000 波特、8N1 与 Linux 交互。

## 只烧录位流 / Linux 下使用

```bash
python3 verify_bundle.py
vivado -mode batch -source board/program_arty.tcl -tclargs toy_a7_uart.bit
python3 host/load.py --port /dev/ttyUSB1 fw_payload.bin
```

Windows 单独调用 Vivado 时可用 `vivado.bat`。单独下载 `.bit` 只配置 FPGA 逻辑；还需
将 `fw_payload.bin` 加载到 DDR 才会启动 Linux。此包不擦写 Flash；掉电后本次 SRAM
配置和 DDR 软件丢失，下一次需要重新执行上述流程。既有 Flash 发布包是另一个目标，
不能用本包 UART 位流直接替代其 MCS。

## 重新构建位流

本包带实际 Chisel 生成 RTL、板级源码、XDC、官方 MIG 输入及本轮构建 Tcl，可直接用
带 Artix-7 支持的 Vivado 2024.1 重建：

```bash
timeout --signal=TERM --kill-after=15s 3600s vivado -mode batch \
  -source board/build_board.tcl -tclargs build/rebuild
```

新生成位流需重新核验时序与 DRC，不能沿用本包摘要。更改 Chisel 时使用对应源码包的
`scripts/elaborate_rob_candidate.sh` 重新生成；默认构建仍是原寄存器 ROB 路径。
完整验证与软件依赖源码在配套 sources 包；许可证和声明在 `LICENSE`、`notices/`。
