# 阶段 03：ROB 优化与 PR10 修复

保留完整 Toy/Linux 的 CPU、虚拟内存、FPU、Gemmini 8×8 和软件 ABI，用 BRAM 换取 ROB
存储逻辑面积，合入 AXI/Tcl 修复；评估和自检属于阶段内部工作。
**当前代码在 [platforms/arty-a7-toy](../../platforms/arty-a7-toy/README.md)**，
本目录保存已经被集成版替代的中间候选和修复记录。

| 分类 | 改动与状态 | 原报告 |
|---|---|---|
| `uart/` | 两份 64 位操作数改 16×128 1R1W BRAM；位流 `dec8dcae…8ee5c` 尚无 PR10 修复 | [报告](uart/2026-10-12/REPORT.md)、[机器结果](uart/2026-10-12/RESULT.json) |
| `fixes/review/` | 两位 AXI SLVERR、Python 显式校验、Tcl 原生异常；当时仅离线验证 | [评估结果](fixes/review/2026-10-12/RESULT.json) |
| `fixes/selfcheck/` | 失败状态、BVALID 背压、错误注入；当时未生成新位流 | [自检](fixes/selfcheck/2026-10-13/REPORT.md) |

ROB 相对阶段 02 UART 减少 **484 LUT、1,657 FF、84 Slice**，增加 **2 BRAM tile**，DSP 不变。
Slice 仍为 98.29%。原默认配置保持寄存器路径，发布候选显式开启 BRAM。
初始记录先于后续两轮实板复测，后续证据关联 [PR #9](https://github.com/DangoSys/fpga/pull/9)。
[integration-inputs/](uart/integration-inputs/MANIFEST.json)保存旧结果绑定的集成源原文，
与原 `sources/` 中的改前输入分开；[旧说明](uart/docs/ROB_RAM.md)为文档快照。

当前集成位流 `9f6f6843…95942` 完成重新生成、实现和 RTL 回归，见
[当前完整报告](../../platforms/arty-a7-toy/evidence/2026-10-13/rob-pr10-full/REPORT.md)。
队友回传单独归档，不回写历史批次资格。当前未验收新版 Flash 冷启动；
MMIO 的 SLVERR 传递也不等同于非阻塞缓存的同步异常保障。
