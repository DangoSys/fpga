# ROB 操作数 RAM 优化报告

本轮通过了 RTL 回归、Linux 启动与完整 FPGA 布线，尚未烧录实板。
不减少架构功能或容量，不替换已有 UART/Flash 发布包。

## 改动与范围

从固定上游 `GlobalROB.scala` 增加可选路径：两份 64 位操作数在 allocation
写入 16×128、1R1W 同步 RAM，利用原 issue pointer 级隐藏读延迟。
控制、依赖、提交顺序与 trace 保留；原指针、背压和有效位控制 RAM 使用。
显式 BRAM 绑定消除了大量操作数 FF，代价是两块 RAMB36。

保留当前 FPGA profile 的 CPU、Sv39、FP16/32/64、Gemmini 8×8、23 项 Ball
指令、16-entry ROB、bank/缓存容量及板级接口。它不会恢复此前已裁剪的独立 Ball。
这项内部存储优化不改变软件 ABI，也不代表整模型编译链已适配。

## 同条件面积与时序

器件 `xc7a100tcsg324-1`，Vivado 2024.1，UART 目标、25 MHz CPU；
沿用原 `board/build_board.tcl`、XDC 和综合/布局策略。基线为
`evidence/2026-10-11/BOARD_RESULT.json`，没有用 Flash 目标作比较。

| 布线后测量 | 原寄存器 | 同步 RAM | 变化 |
|---|---:|---:|---:|
| 物理 LUT（已计入 LUT combining） | 54,413 | 53,929 | −484 |
| FF | 35,600 | 33,943 | −1,657 |
| 占用 Slice / 15,850 | 15,663 | 15,579 | −84 |
| 空闲 Slice | 187 | 271 | +84 |
| BRAM tile / 135 | 29 | 31 | +2 |
| DSP / 240 | 117 | 117 | 0 |
| WNS / WHS（ns） | +1.276 / +0.013 | +1.276 / +0.012 | 均通过 |

候选 TNS、THS 为 0，全部可布线网络完成、布线错误为 0，位流已生成。
运行 1,396 秒，在 3,600 秒期限内完成。DRC 无 Error/Critical，仍有 360 项
普通警告（主要为 DSP 输入/输出流水建议）；CDC 保留 3 项时钟转换 IP 的
CDC-15 Warning，无 Critical。未降低 DRC 严重级别。

全部 64 个 PE 仍各使用一个 DSP。综合阶段减少 429 LUT、1,655 FF；最终以
布线后资源为准。Slice 占用仍为 98.29%，这点余量不能证明能加入另一套算子硬件。

RAM 子层级被 Vivado 归入部分 `bankCols_*` 配置控制，不能把该层级下的约
1,721 LUT 全部解释成 RAM 本体开销。并行提交/配置更新网络仍是后续候选，未在
本轮修改；未测量的优化不计入上述收益。

## 功能与性能核验

- ROB RAM 与原寄存器路径逐周期对照通过，8,029 周期，三个随机种子与两次
  中途复位；接受时保存完整命令作独立对照。断言覆盖满队列、背压及排空。
- 七类 memory 通过原 RTL/独立 scoreboard 对照，包括新增 RAM；AXI、SCU、
  UART/CRC loader 接口检查通过。
- 不改测试二进制，CPU/Sv39/FPU/AMO/cache/IRQ、原 13 项 Gemmini、OS/WS
  分块循环、非对齐/跨页 DMA 分别为 709,434、251,063、684,219、1,914,839
  周期，与原基线完全相同。这是已测用例结论，不是所有负载性能的证明。
- 同一标准 payload 启动 OpenSBI/Linux，通过写时复制、页面保护、浮点进程
  上下文、定时器与总检查；273,506,752 周期与基线相同。页面保护用例故意
  触发子进程 SIGSEGV，之后 `PASS VM_PAGE_PROTECTION` 为预期成功行为。
- Linux 检查使用 AXI 存储模型，串口 RX 输入真实波形；未模拟物理 DDR PHY。

## 复现与文件

从平台目录按 [ROB_RAM.md](../../../ROB_RAM.md) 执行。默认构建保持旧路径，
候选需显式 `sbt -Dfpga.robOperandRam=true`。后续两种配置均重新生成，默认
核心/存储器与旧发布摘要一致，候选与本次已测字节一致，见 `OPTIN_RESULT.json`。

`sources/` 保存本次实际执行的覆盖层、测试入口和板级 Tcl/XDC；其中构造默认
为 true 是首次实验快照，当前集成改为显式开启，生成字节一致性已单独核验。
`INPUT_MANIFEST.json` 记录隔离目录初始输入，`MANIFEST.json` 核验本档案。
`tests/` 保存通过的回归原文，`implementation/` 保存完整资源、时序、DRC/CDC
和 Vivado 日志。无关网络/启动命令错误不作为芯片测试失败写入档案。

生成核心、存储器、位流摘要记录在 `RESULT.json`。大体积 RTL、DCP、位流保留
在构建目录，未当作已验收发布件提交。当前只有 UART 候选；Flash 版本和实板
验收仍需独立执行。原发布资格与本轮记录分开保留。
