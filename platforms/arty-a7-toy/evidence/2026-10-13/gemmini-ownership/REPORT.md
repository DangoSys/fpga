# Gemmini 跨进程所有权：软件候选与离线验证

本轮按用户要求先实现软件串行化，并完成离线验证。板卡暂时无法连接，**没有进行
新实板测试，没有证实原并发卡死已消失，没有修改硬件、位流或 Flash**。
本修改独立于目录归档 PR，以 #10 的 `ccb40f1` 为基线。

## 已完成

- 全部 14 个 Gemmini Linux 程序使用统一入口和固定 `flock` 设备锁，覆盖配置、bank、
  DMA、计算、比较与释放。原 13 项固定参考文件未改；编译副本重命名 `main`。
- 开始使用硬件前写入 DIRTY；正常返回且最后 `bb_fence` 完成后才写 CLEAN。
  超时返回 75；异常后下一调用返回 76，未发送自定义指令；其他锁错误返回 74。
- SIGKILL/非零退出不会因 OS 自动释放锁而恢复设备资格；没有删除锁或自动复位的后门。
- 提供 `same/mixed/cpu/kill` 四类实板对照脚本，随标准共享 overlay 安装到 `/root`。
  看门狗计时子进程会被取消和回收。kill 探针没有捕获活跃所有者时记录 INCONCLUSIVE。

## 有效验证结果

| 验证 | 结果及边界 |
| --- | --- |
| 原生 Linux 协作锁与入口 | 14 类检查通过，6.225 秒；原生 GCC 13.3.0 |
| 真实多进程锁争用 | 6 个进程、120 次事务，临界区重叠 0 次；未执行 Gemmini 指令 |
| 异常/等待 | SIGKILL、非零退出、超时、fork 所有者、残缺记录和符号链接拒绝通过 |
| 实板控制器离线检查 | same/mixed/cpu/kill 原生 mock 通过；不能解释为 FPGA 验收 |
| RV64 静态编译 | GCC 15.3.0，rv64gc/lp64d，-O2/-static，15 个 ELF 通过 |
| 入口与 rootfs | 14 个 ELF 中核验统一 main、workload、drain 和 lease 符号；15 个程序及 helper 摘要匹配 |
| 标准镜像构建 | 固定 bbkernel/Linux/BusyBox/OpenSBI 构建与板级 CLINT 适配通过，158.681 秒 |
| 本版实板单/多进程 | 待连接板卡后执行 |

最终软件镜像 25,797,640 字节，SHA256：
`1b935a57fe08beac3b71a50957dec414bbe86f847b20c10e18c019a7477de48e`。
既有 UART 位流摘要为
`9f6f684361c049527fda09818cc8aa464f1067b75f3762305a27c5c738295942`。
二者分别绑定软件和硬件；原 e2282b5a 软件镜像未加锁，不能用于本版并发验收。
不发布新硬件资格，不继承旧 Flash 冷启动结论，也不改旧 Release 的固定下载入口。

## 队友卡死日志的证据范围

`teammate-concurrency.log` 原样保留附件 `pr10_test_logs.zip` 中的
`newangles_pr10/console.log`。14:03:33 同时启动两个已验证存在的 `/tmp/g`，
600 秒内没有出现返回标记，后续 shell 命令也没有响应。该日志没有保存两个进程的
独立输出、PID 状态或 DMA 波形，因此不能证明某个具体握手环路。
14:13:33 的 mixed 命令发生在已经卡住的系统上，不能算第二次独立复现。
其他目录中 `/tmp/g: not found` 的探针不作为并发故障依据。

## 地址翻译与恢复仍需处理

`audit/MemConfiger.scala` 和当前 GlobalROB 的配置/分组查询以 hart 和 bank/group
为标识，没有 Linux PID 所有权。`audit/TLBCluster.scala` 从 tile 的 CSR 路径取得
PTW status，DMA 请求没有独立 CSR 状态；本锁没有增加提交者页表快照。

固定 bbkernel 配置输入虽写了 `CONFIG_RISCV_ROCC=y`，本次最终
`audit/linux.config` 没有该项；搜索固定 Linux 的 `arch/riscv` 也没有 ROCC 条目。
不能依据输入字符串声称已经启用了内核级加速器上下文管理。
`audit/linux-context.c` 记录普通 Linux 地址空间切换逻辑。这些是核查线索，
不等于已定位硬件卡死根因。文件锁支持 `CONFIG_FILE_LOCKING=y` 及测试 helper
需要的 BusyBox applet 均在实际配置中确认。

正式方案仍需驱动队列、提交者翻译上下文、DMA 缓冲区生命周期，以及可验证的停止/
复位协议。触页/`mlockall` 不能代替驱动的 DMA 页固定与映射管理；参考
[Linux DMA 指南](https://docs.kernel.org/6.6/core-api/dma-api-howto.html) 和
[用户页固定说明](https://docs.kernel.org/6.6/core-api/pin_user_pages.html)。
本版只对遵守运行库的程序提供串行化，不阻止原始自定义指令绕过锁。

## 复现与档案

操作命令、超时与恢复步骤见
[软件所有权指南](../../../software/GEMMINI_OWNERSHIP.md)。
在平台目录运行 `python3 scripts/check_gemmini_ownership.py` 复现原生检查；完整镜像
按原 `software/build_gemmini_image.py` 构建。本轮经用户授权，在服务器新建隔离目录
直接使用原工具链，总超时 3600 秒；构建退出 0。

`HOST_RESULT.json/HOST_host.log` 是原生检查；`LINUX_GEMMINI_BUILD.json` 是软件编译/
rootfs 验证；`RESULT.json` 是 OpenSBI/CLINT 重打包结果；`build.log` 是完整构建原文。
`sources/` 是实际输入，`generated-inputs/` 是实际生成的 CMake、参数、14 项 C 副本及
runtime，`audit/` 是核查源码和实际配置。`INPUTS.json` 与 `MANIFEST.json` 绑定摘要。
这套档案中的 PASS 均有限定范围，不代表实板并发通过。
