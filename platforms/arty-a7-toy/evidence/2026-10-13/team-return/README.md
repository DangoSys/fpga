# 队友实板/PPA 回传：2026-10-13

[PPA_REPORT_PR10.md](PPA_REPORT_PR10.md)为回传原文，对应当前 ROB/PR10、位流 `9f6f6843…95942`。
队友报告完整 DDR 读回 25,797,640 字节、Linux 启动、15 程序与 Gemmini 对照通过，未写 Flash。
尚未附原始机器结果、编程/串口日志和 XADC 采样，按“队友报告通过”单独记录，
不回写发布时 `physical_hardware_tested=false`，不标作本仓库独立核验的完整实板档案。

## 引用时的修正

- 当前总体资源与实现记录一致。
- 原文混用了 UART/Flash 基线：UART 的 Slice 98.82%、核心 WNS 7.567ns、IOB 56；
  98.54%、7.537ns、62 属于 Flash；出处见 [阶段 02](../../../../../history/02-toy-linux/README.md)。
- 对同 UART 基线减少 484 LUT、1,657 FF、84 Slice，增加 2 BRAM；IOB 为 56→60。
  原文 Gemmini 层次基线也取自 Flash，应先统一来源。
- 31.85 MHz 是时序估算，实际 25 MHz；D-cache 路径 slack 改善不能直接归因于 ROB。
- 温度/电压没有给出功耗 W，不能证明功耗降低或不变。

原文保留，修正单列。补入本轮原始日志即可进一步归档，不需因此重跑。
