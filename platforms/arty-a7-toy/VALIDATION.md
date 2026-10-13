# 当前版本验证范围

对象为 `arty-a7-rob-pr10-2026-10-13`、位流 `9f6f6843…95942`、ROB BRAM + PR10、UART。
摘要与提交见 [发布信息](HARDWARE_RELEASE.json)。

[完整报告](evidence/2026-10-13/rob-pr10-full/REPORT.md)和
[机器结果](evidence/2026-10-13/rob-pr10-full/RESULT.json)绑定本版：

- Vivado 完整实现：53,929 LUT、33,943 FF、15,579 Slice、31 BRAM tile、117 DSP。
- WNS +1.276ns、WHS +0.012ns，TNS/THS与路由错误为零；无 Critical DRC/CDC，普通警告保留。
- ROB/存储器/计算单元、真实 CPU 的 Gemmini/FPU/DMA、UART 加载、Linux 五项检查和实际 CDC IP。
- Slice 98.29%，仅余 271，BRAM/DSP 余量不等于足够扩展大量功能。

队友回传本版实板通过的 [PPA 报告](evidence/2026-10-13/team-return/README.md)，原始机器结果、
编程/串口日志尚未随报告提交。后续报告与原始证据分开，不回写发布时的机器状态。
当前未验收新版 Flash 冷启动、整模型或长期 DDR/环境稳定性。
MMIO SLVERR 送到 AXI 输入不等于非阻塞缓存同步访问异常保障；页面保护是独立路径。
频率估算不等于升频实测；温度/电压不等于功耗。

面积比较用 [阶段 02 UART 基线](../../history/02-toy-linux/README.md)：54,413 LUT、35,600 FF、
15,663 Slice、29 BRAM、117 DSP。旧 Flash 属于另一实现。
旧综合/上板说明保留在 [文档快照](../../history/02-toy-linux/uart/docs/VALIDATION.md)。
