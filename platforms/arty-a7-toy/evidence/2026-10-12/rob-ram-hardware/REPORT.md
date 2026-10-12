# ROB RAM 候选实物复测

2026-10-12（Asia/Shanghai）在同一块 Arty A7-100T 上临时烧录 ROB RAM 候选，
沿用先前有效的加载与测试方式。完整镜像读回、Linux 启动和两轮回归通过。
本记录追加到 PR #9；优化源码与完整实现资料来自
[PR #11](https://github.com/DangoSys/fpga/pull/11)，硬件源码提交固定为
`da07b0ab9fa9e8a59819f988eddacf2f3ba2552c`。

## 输入与部署

- 器件 `xc7a100tcsg324-1`，JTAG `210319BCC5FCA`，UART B `210319BCC5FCB` / COM5。
- Vivado 2025.1 临时 JTAG 编程，25 MHz CPU、1 Mbps UART；沿用官方 E.0 MIG。
  板卡 PCB 修订号仍未确认，DDR 接口与之前已实测版本相同。
- 位流 SHA256：`dec8dcaea14b56db49ef8166d1605034695658f55f02dce73d4455fbc078ee5c`。
- 沿用标准 Linux/Gemmini 镜像，25,797,640 字节，SHA256：
  `e2282b5a7ddf1aa01579919aa92df483ed79e739bf5d39530e07532e164118b0`。
- CPU 保持复位，按 256 字节分块写入 DDR，每块读回并核验 CRC、响应序号与全部数据；
  完整一致后才释放 CPU。没有写 Flash，现有 Release 七个附件保持原内容。

## 实测结果

| 检查 | 结果 |
|---|---|
| JTAG 编程、loader 容量/频率 | 通过 |
| 完整 25,797,640 字节镜像读回 | 全部一致，806.265 秒 |
| 首轮加载、启动、15 个程序 | 通过，总计 916.109 秒 |
| 第二轮板上程序摘要 | 15 个均与构建记录一致 |
| 第二轮 15 个程序 | 全部返回 0，123.937 秒 |
| Linux 五项系统检查 | 两轮均通过 |
| 原版 13 项 Gemmini | 两轮均通过 |
| 新增 OS/WS 矩阵逐元素比较 | 每轮 16 项，两轮共 32 项通过 |
| watchdog 正常/非零/刻意超时 | 返回 0 / 1 / 137，全部 watcher 已回收 |
| 回归后交互 shell | 可响应；MemTotal 245,888 KiB，MemAvailable 226,060 KiB |
| UART 延迟清理 | 每次关闭恢复到原 16 ms |

Linux 检查包括写时复制、页面保护、FP64 进程上下文、定时器和总检查。
页面保护用例故意让子进程触发 SIGSEGV；后续 `PASS VM_PAGE_PROTECTION` 和退出 0
是正确结果。watchdog 的 1、137 是预设自检，未发生非预期 workload 失败或超时。
外层实物会话设 3,600 秒期限；单程序板上 90 秒 watchdog、主机等待 120 秒。

第二轮复用首轮完整加载结果，先从真实 Linux 对 15 个文件逐个计算 `sha256sum`，
没有重新烧录或重新传镜像。原始串口日志和结构化返回码通过独立离线核验。
第二轮第 13 项有命令回显交织，原文保留；正式 PASSED 行与返回码仍完整。
不能据此宣称所有串口文本显示行为均已完善。

## 计时与资格边界

两轮 `PERFORMANCE.json` 保存全部 32 项端到端计时。采样有波动，部分小矩阵仍慢于
CPU 参考；不能仅凭两轮计时宣称性能提高。此测试包括分块、DMA、配置、同步与
CPU 跨 K 累加，不能替代硬件跨 K 累加或完整模型验收。

这次证明了 ROB RAM 候选在这块板上可以运行 Linux 和上述 Gemmini 用例。
完整 ISA/FPU 穷举、长期稳定性、热/功耗测量及整模型仍未完成。
它是 UART 临时配置；当前板上运行该候选，掉电后原 Flash 镜像仍负责自主启动。
本轮没有验证候选的 Flash 冷启动，也没有替换旧发布位流。

## 复现与日志

从平台目录执行，位流须来自固定硬件源码的 opt-in 构建；软件可使用已有 UART 包。
替换下列路径与本机串口。新候选必须显式指定摘要，不能使用旧位流的缺省摘要。

```powershell
$sha = 'dec8dcaea14b56db49ef8166d1605034695658f55f02dce73d4455fbc078ee5c'
$bit = 'D:\实际实现目录\toy_a7.bit'
$payload = 'D:\实际软件目录\fw_payload.bin'
$buildRecord = 'D:\实际软件目录\LINUX_GEMMINI_BUILD.json'
$vivado = 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
python host/check_linux_gemmini.py --payload $payload --build-result $buildRecord --bitstream $bit --expected-bit-sha256 $sha --vivado $vivado --port COM5
# 首轮完整成功后复跑；断电或复位后不能沿用 --loaded-run。
$firstRun = 'D:\首轮日志目录'
python host/check_linux_gemmini.py --payload $payload --build-result $buildRecord --bitstream $bit --expected-bit-sha256 $sha --vivado $vivado --port COM5 --loaded-run $firstRun
python host/check_watchdog.py --port COM5 --output build/new-watchdog
python host/check_live_shell.py --port COM5 --output build/new-post
python scripts/verify_linux_gemmini.py --build-record $buildRecord --hardware-result "$firstRun\RESULT.json" --expected-bit-sha256 $sha --output build/new-PERFORMANCE.json
python scripts/verify_rob_hardware.py
```

`first-pass/` 为本次 JTAG/完整读回/启动/首轮原文，`repeat-pass/` 为第二轮与板上摘要；
`watchdog/`、`post-check/` 为清理及回归后状态；`sources/` 保存实际脚本、测试源码与 Tcl。
`software/` 保存构建记录及适配后的 C 输入，`implementation/` 绑定原实现报告与摘要。
其中实现记录的“未做实物验证”是当时的历史状态，本次结论在 `HARDWARE_RESULT.json`。
`MANIFEST.json` 核验全部档案文件；旧测试记录保持原字节，另行追加本次证据。
