# 阶段 02：完整 Toy/Linux 与对应验证

从最早 A7 原型转为完整系统：CPU、Sv39、FP16/32/64、Gemmini 8×8 和 DDR。
本阶段包括 UART/Flash 启动适配、标准 rootfs 打包和 Linux/Gemmini 验证；
软件测试是这个版本的验收工作，不是另一个硬件阶段。

| 分类 | 用途与产物 | 原记录 |
|---|---|---|
| UART 基线 | 临时 JTAG 配置、主机写入 DDR；位流 `ccc33c51…dffde1` | [实现报告](uart/2026-10-11/BOARD_REPORT.md)、[机器结果](uart/2026-10-11/BOARD_RESULT.json)、[首次实板](uart/2026-10-12/README.md) |
| UART 软件/算子验证 | 标准 rootfs、约 25.8 MB 镜像 `e2282b5a…118b0`、15 程序 | [实板报告](uart/linux-gemmini/2026-10-12/REPORT.md)、[输入/日志](uart/linux-gemmini/2026-10-12/README.md) |
| Flash 固化 | Boot ROM 从 Flash 解压到 DDR；位流 `78d2e703…23c18` | [冷启动记录](flash/2026-10-12/README.md)、[机器结果](flash/2026-10-12/FLASH_RESULT.json) |

UART 基线：**54,413 LUT、35,600 FF、15,663 Slice（98.82%）、29 BRAM、117 DSP**，
核心 WNS 7.567ns、IOB 56。Flash：**53,944 LUT、35,645 FF、15,618 Slice（98.54%）、
31 BRAM、117 DSP**，核心 WNS 7.537ns、IOB 62。后续 UART 比较应选 UART 基线。

UART 先完成约 17.4 MB 软件读回、Linux 启动和五项系统检查，后扩展为 15 程序，覆盖原 13 项
Gemmini、16 项矩阵对照和看门狗/收尾 shell。矩阵计时包括 DMA、配置、分块和 CPU 累加，
没有纯 MAC 性能或整模型结论。Flash 独立完成烧写/读回和真实断电重接，使用原系统镜像。

原说明在 [UART 快照](uart/docs/VALIDATION.md)、[软件验证快照](uart/docs/GEMMINI_LINUX.md)、
[Flash 快照](flash/docs/FLASH_BOOT.md)。后续 [阶段 03](../03-rob-pr10/README.md)保留软件 ABI，
继续优化硬件。旧 Flash 仍可恢复，当前适用范围见 [平台 Flash 指南](../../platforms/arty-a7-toy/FLASH_BOOT.md)。
