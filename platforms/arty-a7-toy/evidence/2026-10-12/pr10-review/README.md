# PR #10 离线评估与回归记录

结论及旧基线比较见 [修正说明](../../../REVIEW_FIXES.md)。`RESULT.json` 记录原提交、
当前 ROB 比较提交、五文件摘要、补丁兼容检查和本次测试边界；`MANIFEST.json`
绑定原始结果、日志与实际测试输入快照。历史实现/实物档案未改。

## 通过的检查

- `board-unit/`：Icarus 四组接口回归，包括真实 SCU→平台→CPU 输入端的 B 响应。
- `programming-check/`：20 项 Tcl 返回值、原生异常、配置状态和完整备份检查。
- `flash-guard-check/`：10 项普通/`python -O` 镜像记录校验。
- `session.log`：隔离运行的原始汇总；总 timeout 为 600 秒。

`sources/` 是本次输入快照。CPU 仅使用端口 fixture；未模拟 CPU 行为、物理 MIG，
未访问板卡/串口，未生成或烧录位流。不能将这些结果作为新 RTL 的实物验收。

## 预期失败的反例

- `old-platform-negative.log`：相同平台测试运行旧平台源码，非法 MMIO 地址
  `0x60030000` 的响应为 `01`，预期 `10`；进程退出 1，证明用例能抓住原错误。
  输入为 `old-platform.sv`，其摘要绑定在 `RESULT.json`。
- `original-pr/`：原 #10 的三份 Tcl 原文及离线日志，合法对象/执行记录返回值
  被当成布尔值导致失败。这是 API 契约反例，不是实际板卡编程失败。

## 复现

Linux 下安装 Python、Tcl 8.6 和 Icarus Verilog；在平台根目录执行：

```bash
python3 scripts/check_board.py
python3 scripts/check_programming_scripts.py
python3 scripts/check_flash_guards.py
python3 scripts/verify_pr10_evidence.py
```

Windows 可用 `--tclsh` 指定原生 Tcl 解释器；避免使用不传播子进程退出码的包装脚本。
这些测试自行限制单个子进程的运行时间，CI 另设接口测试 180 秒及任务 10 分钟上限。
