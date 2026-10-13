# ROB 优化与 PR10 修复：完整实现和 RTL 验证

## 结果与产物

本轮采用用户选择的 **ROB 操作数 BRAM + PR10 接口/烧录修复**。两个分支在
`61f4b02` 合并，实际构建输入提交为 `5d20e94`。Chisel 重新生成的核心和存储器
分别与已测 ROB 候选的 `31e7…fb9`、`d5a3…054` 摘要一致；板级源码使用新响应修复。
完整实现和下列 RTL 回归通过，位流为 UART/JTAG **工程预发布**。

| 项目 | 布线后结果 |
|---|---:|
| 物理 LUT / FF | 53,929 / 33,943 |
| Slice | 15,579 / 15,850（98.29%） |
| BRAM tile / DSP | 31 / 117 |
| WNS / WHS | +1.276 ns / +0.012 ns |
| TNS / THS、布线错误 | 0 / 0、0 |
| Error/Critical DRC、Critical CDC | 0、0 |
| 普通 DRC | 360 项，保留原文 |

整板用 Vivado 2024.1，原 25 MHz 约束、原综合/布线策略，不降低 DRC 等级。
实现 1,415.052 秒；timeout 3,600 秒，15 秒强制终止宽限。其他长阶段也有一小时上限，
编译/仿真子进程另设更短超时。资源、周期及警告与旧记录分别比较，不混用 UART/Flash 目标。

位流 SHA256：`9f6f684361c049527fda09818cc8aa464f1067b75f3762305a27c5c738295942`。
软件采用原标准 Linux/Gemmini 镜像，25,797,640 字节，SHA256：
`e2282b5a7ddf1aa01579919aa92df483ed79e739bf5d39530e07532e164118b0`。
下载入口见平台根目录的 [下载说明](../../../ROB_PR10_DOWNLOADS.md)。

## 功能验证

- ROB RAM/寄存器逐周期比较；七类存储器与原 Chisel 模块、独立 scoreboard 全深度/掩码比较。
- PE 原版/LUT/DSP 逐周期比较及量化器形式证明；FMA 三精度原管对照；舍入移位、FPU RF、
  并发 group query、SubROB 流式行与路由检查通过。
- 真实 CPU 全芯片回归：CPU、原 13 项 Gemmini、OS/WS 分块循环、非对齐/跨页 DMA、两组
  各 64 项舍入/移位边界，以及 1,536 项 H/S/D 浮点向量；独立 FMA 基线比较也通过。
- 真实板级 AXI/SCU 的 CPU/Gemmini/loop/DMA 周期分别为 709,434、251,063、684,219、
  1,914,839，与旧 ROB 同条件基线一致。
- UART RTL 不预加载 DDR、不强制释放 CPU，完整加载/读回 110,592 字节后验证 RUN，
  再执行原 CPU 程序，61,853,990 周期通过。
- 最新标准镜像启动 OpenSBI/Linux，UART 输入命令，COW、页面保护、FP64 进程上下文、
  定时器、系统检查通过，340,774,843 周期。镜像大于旧 ROB Linux RTL 用例，不据此比较性能。
- 实际 Xilinx AXI Clock Converter IP 仿真通过 90 个读 beat 及不同大小、并发、背压和边界。
  四组接口、20 项 Tcl、10 项普通/-O 镜像校验、入口失败状态及 RTL 注入反测再次通过。

## MMIO 观察与验收边界

补充用例由真实 CPU 发起非法 MMIO 读写，检查 SLVERR 完整传到 CPU AXI 输入；旧平台
反测按预期失败。该用例观察到 **0 个同步 trap**。现有 Rocket 非阻塞缓存不保证把外设
总线错误转为同步访问异常，不能将两位响应修复等同于完整物理总线错误保护。此行为
与 Linux 已验证的虚拟内存页面保护路径不同；没有为通过测试而修改缓存或放宽总线断言。

用户确认本轮无法接板卡，选择先上传实现/RTL 验证的工程预发布。因此没有本轮实物、
真实 DDR PHY 或 Flash 冷启动资格，旧硬件记录保持历史原字节，不继承其结论。
Xilinx FIFO 行为模型不模拟真实同步延迟；静态 CDC 与 IP 功能仿真不能替代实物验证。
整模型推理、长期 DDR 压力和环境稳定性尚未验收。

## 复现和证据

`RESULT.json` 汇总精确摘要、范围、资源和时间；`INPUTS.json`/`sources/` 绑定实际输入，
`implementation/` 保存全部实现原文，`tests/` 保存成功回归及有用的预期失败反例。
最新软件源与构建记录仍在原 Linux/Gemmini 档案。生成的大型 RTL/位流提供于下载包，
Linux 的 payload.hex 可从固定摘要的二进制重新生成，避免重复存入 Git。

`run-fullcheck.sh` 是本次实际命令顺序，`toolchain.sh` 记录已安装工具路径；换机器时
配置同版本工具，并用脚本的 `--repository`、`--baseline-core` 参数指定自己的只读输入。
使用 `scripts/elaborate_rob_candidate.sh` 显式启用 RAM；默认生成仍保留原寄存器配置。
