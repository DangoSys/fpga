# Gemmini Linux 设备所有权与并发对照

本修改先用**跨进程串行化**隔离指令交错问题。多个程序可以等待设备，硬件一次执行
一个完整程序。尚未做本版实板回归，不把离线通过解释成并发死锁已经修复。
硬件、ISA、8×8 阵列、位流和旧 Flash 镜像均不变。

## 锁覆盖什么

`prepare_gemmini_linux.py` 为全部 14 个 Gemmini 可执行文件接入统一入口：

```text
flock 获取同一设备锁（最多等待 90 秒）
核验 CLEAN → 写入 DIRTY → 开始硬件操作
完成同步 → 原 workload：分配 bank、配置、DMA、计算、结果检查、释放 bank
再次 bb_fence，等待最后的释放命令完成
workload 返回 0 且完成同步成功 → 写入 CLEAN → 关闭锁文件
```

原 13 项参考源码保持原摘要，只在生成副本时调整 DIM 并在编译时重命名 `main`。
新增分块矩阵程序也使用同一入口，CPU/Linux 系统检查不占锁。每个参考程序本身会
重新配置数据流、转置及移位参数。入口不会释放未分配的 bank，也不保存硬件上下文。

锁文件固定为 `/tmp/buckyball-gemmini.lock`；当前 rootfs 按同一个 root 用户运行测试。
使用 `flock`、`O_CLOEXEC`、单调时钟期限，拒绝符号链接、残缺记录和错误所有者。
`fork` 子进程不能把父进程的记录改成 CLEAN。

| 情况 | 行为 |
| --- | --- |
| 成功并完成最后的 fence | 清除 DIRTY，允许下一个程序 |
| 等待超过 90 秒 | 返回 75，未发送任何加速器指令 |
| 上一个程序被杀、崩溃或返回失败 | DIRTY 保留；后续程序返回 76，未发送指令 |
| 文件访问/记录写入失败 | 返回 74，拒绝进入或保留未知状态 |

**不要删除、截断或更换锁文件来恢复。** 信号退出/OS 释放锁不表示 DMA 已经停止。
本阶段没有可证明安全的设备局部 abort/reset。恢复必须复位完整 FPGA/CPU/加速器，
通过既有加载流程重新装入并启动 Linux；只重启 shell 或 Linux 进程不够。
该锁是合作协议；绕过运行库直接发自定义指令的程序仍能破坏设备状态。

## 离线复现

在 Linux 主机运行，无需 FPGA，也不会执行自定义指令：

```bash
timeout --signal=TERM --kill-after=5s 60s python3 scripts/check_gemmini_ownership.py
```

包含 6 进程/120 次争用、等待超时、SIGKILL、失败后的拒绝、继承锁、残缺记录、
入口顺序，以及实板 shell 控制器的四类原生 mock 测试。结果在
`build/gemmini-ownership-host/{RESULT.json,host.log}`；明确标注 `hardware_tested=false`。
CI 使用同一入口。完整镜像沿用 [标准 CMake/bbkernel 构建](GEMMINI_LINUX.md#准备与构建)，
构建器检查 15 个 RV64 ELF、14 个设备所有权入口和 rootfs 文件摘要。

## 实板验收：待执行

使用既有 ROB/PR10 UART 位流与**本次新构建的** `fw_payload.bin`、
`LINUX_GEMMINI_BUILD.json`，先运行原 `host/check_linux_gemmini.py` 的完整
DDR 读回、Linux 启动和 15 程序单进程回归。位流需显式指定当前发布摘要
`9f6f684361c049527fda09818cc8aa464f1067b75f3762305a27c5c738295942`。
旧 Release 包中的软件没有这个锁；只运行旧一键下载入口不会验证本修改。

新镜像在 `/root` 内包含 `gemmini_concurrency.sh`。每种对照从干净平台启动开始：

```sh
cd /root
sh gemmini_concurrency.sh same   # 两个分块矩阵程序，同时提交
# 完整复位并重新加载 Linux 后，再选下一种：
sh gemmini_concurrency.sh mixed  # OS CISC 与 WS RISC，配置不同
sh gemmini_concurrency.sh cpu    # 两个 Gemmini 程序 + CPU 负载
sh gemmini_concurrency.sh kill   # 停止并杀死已持锁程序，后续程序必须拒绝
```

脚本记录实际 ELF 摘要、PID、独立程序输出、返回码、超时标记和正常测试耗时。
正常对照限 180 秒；异常后拒绝检查限 10 秒。正常验收必须两个程序结果正确、
均完成、锁为 CLEAN，并能继续操作 shell。kill 测试若未捕获活跃所有者，返回 77
并标记 INCONCLUSIVE；不会当成通过，也不会声称捕获了某个确定 DMA 阶段。
保存串口原始日志及 `/tmp/gemmini-ownership-*` 文件。若 CPU 卡在不可中断的自定义
指令，板内 watchdog 也可能无法调度，主机须保留独立超时，并完整复位后再测。

## DMA 上下文审计结论

当前 bank/ROB 所有权按 `hartId/vbankId/groupId`，同一 hart 上的 Linux PID 不会
因此自动隔离。固定上游的 `TLBCluster.scala` 从 tile 的 CSR 路径取得 PTW status，
DMA 请求未携带独立 CSR 状态。因此加锁能阻止合作程序交错发指令，仍不能证明
进程切换、加速器 TLB 失效和页表遍历始终使用提交者的地址空间。

原 `bb_dma_touch` 解决输出零页/COW 的触页问题；它和 `mlockall` 都不等同于驱动
为 DMA 管理缓冲区生命周期。正式修复需要统一驱动队列、提交者地址空间/翻译上下文、
正确的页固定或驱动 DMA 缓冲区，以及可验证的停止/复位协议。参考
[Linux 6.6 DMA 指南](https://docs.kernel.org/6.6/core-api/dma-api-howto.html) 与
[用户页固定说明](https://docs.kernel.org/6.6/core-api/pin_user_pages.html)。
不能把物理地址直接传入现有虚拟地址指令接口，也不能把软件锁称为完整进程隔离。
