# FPGA

将 [Buckyball](https://github.com/DangoSys/buckyball) 适配到 FPGA。
当前 A7 入口为 **Arty A7-100T 的 Toy/Linux ROB/PR10 UART 集成版**。

## 当前平台

| 目标 | 使用方式 | 说明 |
|---|---|---|
| 当前 Toy/Linux UART | 临时 JTAG、UART 加载与 Linux/Gemmini 回归 | [平台](platforms/arty-a7-toy/README.md)、[直接运行](platforms/arty-a7-toy/HARDWARE_TEST.md) |
| 旧 Flash 恢复方案 | 对应 Flash 组合掉电启动 | [版本与流程](platforms/arty-a7-toy/FLASH_BOOT.md)，不能套用当前 UART 位流 |
| Kintex-7 `xc7k160tffg676-2` | 原 P2E 示例 | [K7 指南](platforms/xc7k160t/README.md)，独立于 A7 迭代 |

Windows 进入 `platforms/arty-a7-toy`，替换真实串口和 Vivado 路径：

```powershell
python -m pip install -r host/requirements-hardware.txt
.\run_hardware.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

自动取固定发布包并复用原验证器，无需重建硬件/Linux 或登录服务器；无板可用 `-PrepareOnly`。
当前整理版位于 `codex/organize-history` 分支，未合并时的 Git 获取方式见验证指南。
硬件/接口集成来自 [PR #10](https://github.com/DangoSys/fpga/pull/10)，目录整理单独提交。

## 阶段与历史

[history/](history/README.md)按三大阶段整理：**①早期 A7 原型 → ②完整 Toy/Linux
（UART/Flash 与对应验证）→ ③ROB 优化与 PR10 修复**。
旧工程、旧说明和旧证据分类归档；当前源码、运行入口和当前证据保留在平台目录。
报告绑定各自的位流/软件，不能混用不同启动路线、版本的 PPA 与验收结论。
