# Toy 8×8 Arty A7-100T 整板实现核验

2026-10-11，Vivado 2024.1，器件 `xc7a100tcsg324-1`。

**整板布局布线、时序、CDC 检查及 bitstream 生成通过；板级 RTL 的 Linux 用户态检查通过。**
尚未在实物验证 DDR 校准或 Linux；板卡硬件 revision 未知，当前采用官方 Digilent E.0 MIG 工程参数。
不能把 RTL 仿真或 bitstream 生成当作实物上板成功。

## 保留功能与板级接口

保留此前已验证的 Chisel Toy 核心：RV64 CPU、M/S/U、PMP、Sv39、FP16/32/64 共享 FMA、
I/D cache、Gemmini 8×8、64 个 DSP PE、64 KiB 加速器 SRAM 与现有 23 个 opcode。
核心 RTL SHA256 未变：`4c6aacf64660bbbf14b1114e8d5e4439d6a4e1427aaf1f681c6a4f618f2d2779`。本轮没有继续裁剪核心功能。

加入官方 MIG 256 MiB DDR3L、实际 Xilinx AXI Clock Converter、窄访问转全宽 DDR 适配器、
SCU 控制台、CRC 串口加载/读回、时钟、复位和板级引脚约束。
100 MHz 板载时钟生成 25 MHz 核心、166.67 MHz MIG 输入和 200 MHz 参考时钟；
MIG UI 83.33 MHz，CLINT 实际 500 kHz，串口 1 Mbps、8N1。

DDR 地址 `0x80000000..0x8fffffff`；SCU EXIT `0x60000000`，TX/RX/STATUS
`0x60020000/04/05`。串口 RX FIFO 为 256 字节。OpenSBI 适配实际计时频率和 CPU DTB 属性；
Linux/BusyBox Image 与原版本相同，没有去除虚拟内存、FPU 或 Linux。

## 最终整板实测

| 项目 | 布线后 | A7-100T 容量 |
|---|---:|---:|
| 物理 Slice LUT | 54,413 | 63,400 |
| 占用 Slice | 15,663 | 15,850 |
| FF | 35,600 | 126,800 |
| BRAM tile | 29 | 135 |
| DSP | 117 | 240 |
| WNS / TNS | +1.276 ns / 0 | |
| WHS / THS | +0.013 ns / 0 | |

LUT 余量 8,987（14.18%）；建立/保持违例端点均 0。
Slice 占用 98.82%，只余 187 个，控制集 1,256 个。
尽管已经完成布线，布局打包仍紧，LUT 余量不能当作可自由增加功能的空间。
LUT6 原语 20,797 是子项；判断容量使用包含各输入规模和 RAM 的物理 Slice LUT。
95,231 条可布线网络全部布通，路由错误 0。
整板最大/最小时序涵盖实际 MMCM、MIG 和 CDC，不能用单独的核心 OOC 时序替代。
10 项总线偏斜约束通过，最差裕量 10.844 ns。

`AreaOptimized_high`、`resource_sharing on` 与 `ExploreArea` 保持输入 RTL 不变。
最终采用完整复位修复版构建，未采用后续两项打包试验。
等效驱动合并在旧复位网表上曾减少 Slice，但在相同修复版综合检查点上重跑后，
LUT 从 54,413 降至 53,976，Slice 却从 15,663 增至 15,778（99.55%）；
因此保留 Slice 余量更好的 15,663 版本。低扇出使能重映射也因 LUT 增加而未采用。
这些测量及合并版 bitstream 保留为比较证据，不作为推荐上板版本。
加载器 INFO 改为直接生成回复字节，使 256 字节 staging RAM 恢复 LUTRAM 推断。
之前默认策略整板综合 64,077 LUT、布局失败；失败日志及检查点保留，不与最终布线结果混用。

## CDC、约束及警告

CDC Critical 为 0。MIG 复位改为参考时钟域的同步按钮和寄存器输出，解决上轮两项
CDC-10（同步器前组合逻辑）；没有降级 severity 或建立 waiver。
修复版综合快照仍报告两条 MIG 内部辅助复位链；这些无用路径在实现优化后被移除，
最终严格零 Critical 检查通过。历史分析保存在 `evidence/synth-cdc-review`，不参与构建放行。
CDC-15 警告来自 Xilinx AXI 异步 FIFO 的 RAM 读使能结构，实际 IP 功能回归通过，
相应跨域最大延迟及总线偏斜约束通过；功能模型不模拟亚稳态。

内部未约束端点、无时钟、组合环路等检查均为 0。缺少同步 I/O 延迟的端口仅为
异步 BTN/UART 输入、LED/UART 输出和 MIG 管理的 DDR RESET_N，均有对应定点例外。
DDR 数据、地址、控制及所有内部 CPU 路径保留时序检查。DRC 无 Error/Critical Warning；
原始 DSP 流水建议、MIG PLL 混合缓冲、MIG 内部复位 LUT、D-cache SDQ 可能读写碰撞、
缺少同步器属性和控制集数量等方法学警告完整保留，未声称全部消除。

## 功能证据

| 原有二进制经板级 AXI/SCU | 结果 | 周期 |
|---|---|---:|
| cpu | PASS | 709,434 |
| gemmini | PASS | 251,063 |
| loop | PASS | 684,219 |
| dma | PASS | 1,914,839 |

原 CPU 程序和比较预期不变。另有 AXI、SCU、CRC loader 三项单元回归，以及实际 Xilinx
CDC IP 的 90 个读回拍：覆盖 8..128 bit 访问、INCR/FIXED、字节掩码、并发读写、停顿、ID
及非法地址/跨 4 KiB 拒绝。SCU 测试包含 200 字节缓冲和读回。

串口启动测试经真实 UART 引脚信号写入并逐字节读回 110,592 字节原 CPU 程序，
拒绝坏 CRC/RUN，随后真实 RUN 释放 CPU 并通过原 CPU oracle；没有预加载 DDR 或强制启动。

Linux RTL 仿真启动 OpenSBI、Linux 6.6 和 BusyBox，经真实 UART RX 输入
`/root/linux_system_check-linux`，COW、页保护、FP64 进程上下文、定时器及总检查通过。
共 273,506,752 核心周期；UART 输入 overflow/framing 均为 0。
先前结束监测少取一个字符，导致已有 PASS 输出后仍超时；失败日志保留，修正监测后重新运行通过。
这些仿真用停顿 AXI 存储模型替代 DDR PHY；Linux bench 直接释放启动，加载器另行验证。
没有布线后功能仿真或功耗实测。Gemmini 任意尾维度、跨 K-tile 累加等原有覆盖边界见
`GEMMINI_CORRECT_REPORT.md`，未扩充为未经测试的完整算子覆盖。

## 文件、超时与使用

整板目录 `build/board-20261011-132657`；bitstream `toy_a7.bit`，布线检查点 `routed.dcp`。
整个 Vivado 进程组硬超时 3,600 秒，TERM 后 15 秒 KILL；实际 1406.2 秒，未触发。
368 份文件下载后核验远程 SHA256，机器结果 `BOARD_RESULT.json`。
bitstream SHA256：`ccc33c511e613561fb9dd1e9c847bd3b84037da1d078c44cd3de197d55dffde1`。

加载镜像 `build/board-software/fw_payload.bin`，17,409,032 字节，
SHA256 `eb2ee34cc1a744498ac63b4e3fae425d4bb06be422ae6d41bd1ead696201134f`。确认实物 DDR/revision 与目标兼容后才使用该工程 bitstream；
加载方式、LED 含义及复现命令见 `board/README.md`。本轮没有烧录或新建 PR。
