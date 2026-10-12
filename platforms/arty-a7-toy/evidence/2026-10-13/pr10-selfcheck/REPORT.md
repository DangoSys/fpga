# PR #10 新版自检报告

## 结论

自检基线为 `9fdcec6`。本轮未发现新增生产 RTL/Tcl/镜像校验的功能错误，发现并修正
两处验证缺口。生产 RTL、烧录 Tcl、芯片配置和固件保持该基线字节；修改仅涉及测试、
结果记录、文档及 CI。没有生成或烧录新位流，也没有取得新增实物验收。

## 自检发现与修正

| 发现 | 反证 | 修正 |
|---|---|---|
| 复跑失败可能保留旧 PASS | 给三个实际入口预置旧 PASS，再注入首个检查失败；旧版本均退出 1，但文件仍为 PASS | `offline_check.py` 在启动时写 RUNNING，异常时写 FAILED；三入口再次注入均得到 FAILED |
| 平台用例没有检查 BVALID 持续性 | 只在 build 副本将 SCU 的 BVALID 清除条件改成无视 BREADY；旧测试仍通过 | 每个背压周期检查 CPU 输入 BVALID/响应/ID，并检查握手后 BVALID 撤销；新测试在 valid=0 处失败 |

“PASS_MUTATION_ORACLES”表示检错能力符合预期：旧测试漏检的反例应退出 0，
新测试拒绝错误应退出 1，不表示注入错误的 RTL 正确。错误副本不会替换生产源码。

## 本轮结果

- 四组接口回归通过：AXI fullwidth、SCU、平台响应、DDR UART loader。
- 20 项 Tcl 返回值/异常/状态/备份检查、10 项普通/-O 镜像校验通过。
- 三个实际检查入口的失败状态注入通过，复跑失败不再遗留 PASS。
- 三项 RTL 注入反测符合预期；新增用例也再次抓住旧平台的 `10→01` 响应错误。
- 原 2026-10-12 的 77 项评估档案、所有既有实现和实物档案保持原字节。

主要回归在服务器独立目录运行，总 timeout 为 600 秒；公开注入脚本另设外层
180 秒和每个编译/仿真进程 60 秒。结果、输入摘要及范围在 `RESULT.json`，原文日志
在各测试目录，实际输入快照在 `sources/`。`stale-baseline/` 保存旧版本的预期失败证据。
这些都是离线验证，CPU 仅为端口 fixture，未模拟 CPU 行为、物理 MIG 或实际 Vivado
烧录过程；不能据此认定新位流已通过硬件验收。

## 复现

Linux 下安装 Python、Tcl 8.6、Icarus，在平台根目录执行：

```bash
python3 scripts/check_board.py
python3 scripts/check_programming_scripts.py
python3 scripts/check_flash_guards.py
python3 scripts/check_runner_status.py
python3 scripts/check_platform_mutations.py
python3 scripts/verify_pr10_evidence.py
```

需要复现旧 PASS 问题时，确保 Git 本地包含 `9fdcec6`，执行
`python3 scripts/check_runner_status.py --baseline-ref 9fdcec6`。这会使用旧入口的隔离副本，
不会改动当前入口。该命令会写入 runner-status-check，之后可再执行普通模式恢复当前检查结果。
