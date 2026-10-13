# PR #10 评估与修正

先评估原提交 `f20b504`，再修正。本次保持已有芯片配置和公开验收记录，
不重新编程板卡、不修改 Flash，也不把旧位流认定为已包含新的 RTL 修复。

## 与当前版本的关系

#10 基于 main `4bdd4e4`。逐文件比较发现，它涉及的五个文件在当前 ROB 工作分支
`8f7bd63` 中仍与该基线逐字节相同，因此问题没有因 ROB 优化或新日志而消失。
五文件局部补丁对当前分支执行 `git apply --check` 通过。修正没有复制旧 chip
配置、恢复旧 RTL 核心或覆盖 #9/#11 的新资料。

## 逐项结论

| 原改动 | 评估 | 最终处理 |
|---|---|---|
| `scu_bresp` 去掉归约 OR | 正确；`10` 被压成 `01`，SLVERR 误变 EXOKAY | 保留；增加真实 SCU 到 CPU 输入端口的测试 |
| 预打包镜像的 `assert` 改显式异常 | 正确；`python -O` 会删除 assert | 保留；对四项记录字段做普通/-O 篡改检查 |
| 三个 Tcl 入口用 `!命令返回值` | 缺乏统一布尔返回值依据；可拒绝合法成功 | 改用原生 Tcl 异常处理，增加配置状态检查 |

本机 Vivado 2025.1 随附文档及
[UG835 设备命令](https://docs.amd.com/r/2025.1-English/ug835-vivado-tcl-commands/program_hw_devices)
描述硬件对象/执行记录返回值；
[Flash 命令](https://docs.amd.com/r/2025.1-English/ug835-vivado-tcl-commands/program_hw_cfgmem)
描述成功返回记录、失败报错。没有支持“这三个命令统一失败返回 0、不抛错”的依据。
离线按兼容返回值注入，原 #10 的三个脚本都在成功路径报布尔类型错误。
本机实际 `vivado.bat -mode batch` 执行只含 `error` 的离线脚本，退出码为 1。
这验证错误传播，不是一次真实编程失败实验。

最终 Tcl 通过 `catch` 的状态识别异常，保留原错误选项；JTAG/Flash bridge
编程后刷新并要求 DONE/EOS 为 1、CRC_ERROR 为 0。Flash 备份命令成功且完整
16 MiB 后才允许擦写；编程/verify 报异常就停止，不打印成功标志。

## 对原 PR 其他观察的评估

- `axi_fullwidth` 的 `addr + len×bytes_per_beat` 表示最后一拍起点，配合已有
  对齐和大小检查可以判定范围；不能直接改成 `len+1`。跨 4 KiB 拒绝符合
  [AXI 协议要求](https://docs.amd.com/r/en-US/pg101-axi-protocol-checker/AXI-Protocol-Checks-and-Descriptions)。
  这部分 RTL 本次保留原值。
- Flash observer 对瞬时断连可能报假失败的观察有合理性；改变它可能影响真实
  冷启动的断连语义，本次不改。
- 异步构建 worker 的退出码不足以表达任务最终状态，这个观察成立；现有
  `RUN.json`/位流检查契约保留，本次不扩展到构建调度器。

## 验证与资格

- 原 #10 Tcl 的成功路径错误已离线复现；修正后 20 个返回值、异常、DONE/EOS/CRC
  与短备份用例通过。fixture 不加载 Vivado，不连接硬件。
- Python 普通/-O 两种模式，各覆盖有效记录及四项篡改，共 10 项通过；使用
  替代 Observer 在编程边界停止，测试不会访问串口或执行 Vivado。
- 接口回归四组通过：原 AXI fullwidth、SCU、DDR loader，加新增平台 B 响应。
  新用例使用实际平台与 SCU，检查正常写、非法地址、非对齐和错误 burst，
  从 CPU 输入端检查响应、ID 及背压稳定性。仅使用 Chisel 端口 fixture，未模拟 CPU 行为。
- 同一用例对当前旧平台反测，在 `0x60030000` 得到 `01` 而预期 `10`，按预期失败；
  修正版本通过。日志索引在 [阶段 03 接口评估档案](../../history/03-rob-pr10/fixes/review/2026-10-12/RESULT.json)。

SOURCE_LOCK 更新当前源码摘要；历史 Tcl/位流/实物日志保持原字节。
历史验收校验绑定归档中的原脚本，当前脚本由新摘要与测试绑定，不继承原脚本实物资格。
核心生成摘要仍保留原值。板级 RTL 已变，新位流还需重新综合、布线和实物验收；
2026-10-12 的 ROB 实板记录使用 #11 的旧接口版本，未包含本次 AXI 修复。

## 2026-10-13：新版自检

自检发现并修正两处验证问题：复跑失败可能遗留旧 PASS 结果；原平台测试未直接检查
背压期间 BVALID 持续有效。新的离线入口启动即写 RUNNING，异常写 FAILED；平台用例
同时检查 BVALID/响应/ID，并检查响应握手后有效信号撤销。
原四组接口、20 项 Tcl 和 10 项镜像检查再次通过，新增实际入口失败注入和 RTL 错误
注入证明两个缺口已堵住。测试源码、日志与精确边界见
[自检报告](../../history/03-rob-pr10/fixes/selfcheck/2026-10-13/REPORT.md)。原 10 月 12 日档案保持原字节。
