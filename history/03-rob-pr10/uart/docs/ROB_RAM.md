# ROB 操作数存储优化

本轮保留 CPU、Sv39、完整 FPU、Gemmini 8×8、23 项 Ball 指令、16-entry ROB、
bank/缓存容量和板级端口，将 ROB 的两份 64 位操作数移入同步 RAM。
改动在 Chisel 覆盖层，生成的 RTL 不手工重写计算逻辑。

## 实现方式

`patches/framework/GlobalROB.scala` 的 `useOperandRam` 默认关闭，保留原发布路径。
用 `sbt -Dfpga.robOperandRam=true` 显式启用；单元测试直接指定两条路径进行比较。
新 RAM 为 16×128、1R1W，allocation
写入，选中 issue 指针时读取。既有指针级提供读取周期，背压期间重复读取该指针；
替换指针时，旧响应先进入既有 payload 级，新读取在下一个周期到达。
控制标志、依赖状态、MSET 提交小字段仍用寄存器。

原完整寄存器观察用于 DPI trace/commit，不删调试语义；DPI disabled 的 FPGA
综合会消除仅被调试使用的数据位。禁止同址读写的断言有效，RAM 内容不复位，
有效位和发射状态仍复位。复位后不会把旧 RAM 数据当作新指令执行。

`prepare_fpga_memories.py --block-memory robOperands_ext` 显式选择 BRAM；浅层
其他 RAM 的原映射策略不变。`prepare_rob_candidate.py` 核验全部架构 profile
字段与旧目标相同，并核对既有 memory 几何参数，之后只对新 RAM 指定 BRAM。

## 已完成的功能验证

- RAM/register 路径逐周期比较通过，共 8,029 周期，含满队列、绕回、背压和两次
  中途复位；另以接受时保存的完整命令核验 issue 操作数，避免两条路径共同出错漏检。
- 七类 memory 与实际原 Chisel RTL/独立 scoreboard 比较通过，覆盖全部深度、
  写 mask、enable、双端口定义内行为及两拍之间输出稳定性。
- 板级 AXI、SCU、CRC loader 检查通过；原测试二进制不改，四组周期数与基线完全相同：

| 用例 | 基线周期 | 候选周期 |
|---|---:|---:|
| CPU/Sv39/FPU/AMO/cache/interrupt | 709,434 | 709,434 |
| 原 13 项 Gemmini | 251,063 | 251,063 |
| OS/WS 分块循环 | 684,219 | 684,219 |
| 非对齐/跨页 DMA | 1,914,839 | 1,914,839 |

完整生成与绑定已通过；候选核心 SHA256 为
`31e7e07f94d08208dbb564edf9546240df26ff834935bfb646b71b541d875fb9`。
Linux RTL 启动、串口命令和五项用户态检查通过，273,506,752 周期与基线相同。
25 MHz UART 整板实现通过并生成位流；完整报告见
[本轮记录](evidence/2026-10-12/rob-ram/REPORT.md)。该初始档案保持实现阶段的历史状态。
后续实物复测已通过完整镜像读回与两轮各 15 个 Linux/Gemmini 程序，新增记录在
[PR #9](https://github.com/DangoSys/fpga/pull/9)，绑定同一份候选位流摘要。

| 布线后资源 | 同条件 UART 基线 | ROB RAM 候选 | 变化 |
|---|---:|---:|---:|
| 物理 LUT | 54,413 | 53,929 | −484 |
| FF | 35,600 | 33,943 | −1,657 |
| 占用 Slice | 15,663 | 15,579 | −84 |
| BRAM tile | 29 | 31 | +2 |
| DSP | 117 | 117 | 0 |

空闲 Slice 从 187 增至 271，占用仍为 98.29%，不能据此判断足够恢复其他 Ball。
WNS +1.276 ns、WHS +0.012 ns，无布线错误或 Critical DRC/CDC；普通警告保留。
DSP 仍包含全部 64 个 PE。这里比较 UART 目标，未混用 Flash 目标的资源报告。

## 复现候选

在隔离 Linux 工具链目录执行，原基线 SRAM 清单从已验证旧版本的
`build/serial-bound/MEMORY_MANIFEST.json` 取得；不能传入候选自身的清单。
构建代理仍遵守 AGENTS 的 MCP 规则，本轮用户已明确授权隔离直接调用作为例外。

```bash
bash scripts/elaborate_rob_candidate.sh
python3 tests/check_fpga_memories.py --original build/serial-reference/ToyLinuxChip.sv --bound build/serial-bound
bash scripts/build_test_programs.sh
python3 scripts/run_board_regression.py
VIVADO=/path/to/vivado python3 scripts/start_rob_board_build.py
bash software/build.sh
python3 scripts/check_board_linux.py
python3 scripts/verify_rob_evidence.py
```

回归需按原流程准备 `cpu-smoke`、`gemmini-tests`、`loop-stress` 和 `dma-beat64`
测试二进制；本次从旧隔离目录只读复用并在结果里记录摘要。Linux 检查使用同一份
原标准 payload，执行 `scripts/check_board_linux.py`，结果在 `build/board-linux-final/`。

候选 launcher 使用原整板 Tcl、原 25 MHz 约束和原策略，外层一小时 timeout。
其结果不继承旧实物资格。默认 `elaborate.sh` 仍受旧 `verify_target.py --core`
摘要门限保护；候选走上述独立入口和 `verify_rob_evidence.py --core`。
后续候选已临时上板并通过上述回归；其 Flash 启动版本仍未生成或验证，
现有发布包不替换。
