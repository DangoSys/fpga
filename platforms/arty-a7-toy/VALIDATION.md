# Validation and remaining hardware acceptance

Measured with Vivado 2024.1 on `xc7a100tcsg324-1`, using the exact Chisel core
hash `4c6aacf64660bbbf14b1114e8d5e4439d6a4e1427aaf1f681c6a4f618f2d2779`.
Read [the preserved detailed report](evidence/2026-10-11/BOARD_REPORT.md) and
[machine record](evidence/2026-10-11/BOARD_RESULT.json) for provenance and scope.

| Complete routed board | Result |
|---|---:|
| Physical Slice LUT | 54,413 / 63,400 (85.82%) |
| Occupied Slice sites | 15,663 / 15,850 (98.82%) |
| FF / BRAM tiles / DSP | 35,600 / 29 / 117 |
| Gemmini PE DSP | 64 |
| WNS / WHS | +1.276 / +0.013 ns |
| TNS / THS / routing errors | 0 / 0 / 0 |
| Fully routed nets | 95,231 |
| CDC Critical / worst bus-skew slack | 0 / +10.844 ns |
| DRC Error or Critical Warning | 0 |
| Full build / timeout | 1,406.2 / 3,600 seconds |

Only 187 Slice sites remain. The 8,987 remaining LUTs cannot be treated as free
placement capacity. The LUT6 primitive count, 20,797, is a subset of physical
LUT utilization. An equivalent-driver merge was rejected: it reduced LUTs to
53,976 but increased occupied Slice sites to 15,778. No further core cuts were
made to obtain the selected result.

## Functional checks

- Original CPU/Sv39/FPU/AMO/cache/interrupt oracle through board AXI/SCU:
  709,434 cycles. Original Gemmini: 13/13, 251,063 cycles.
- Correct-comparison 40 alternating OS/WS loops: 684,219 cycles; unaligned and
  cross-page DMA: 1,914,839 cycles. Test expectations are preserved.
- Fullwidth AXI, SCU and CRC loader unit tests; 200-byte SCU FIFO buffering.
  Actual Xilinx CDC IP passes 90 read beats at 25/83.33 MHz independent clocks.
- Real UART RTL signals load and read back all 110,592 original CPU-program
  bytes, reject corrupt requests and release CPU only through RUN; original
  oracle passes. No preloaded DDR or forced CPU release in that test.
- OpenSBI/Linux 6.6/BusyBox RTL boot: COW, page protection, FP64 process context,
  timer and overall system-check PASS, 273,506,752 cycles. The page-protection
  test deliberately causes a child SIGSEGV; its parent checks the expected fault.

Linux testing directly releases the CPU; the loader is verified independently.
RTL simulations substitute a stalled AXI memory model for the DDR PHY. CDC
functional models do not simulate metastability. No routed-netlist functional
simulation or power measurement is claimed. Gemmini stress coverage is limited
to M8/N32/K8, shift zero and no loop bias; arbitrary tails, cross-K-tile loop
accumulation and loop bias are not established by that test.

## Package reproducibility

The staged repository package was separately relocated into a fresh Linux
directory. Scala/Chisel and OpenSBI were recompiled: generated core/RAM and the
payload exactly match the hashes above. AXI/SCU/loader tests and Python/Bash
syntax checks pass. Pinned dependency exports and the already built Linux image
were reused; the kernel was not rebuilt in this packaging check. The explicit
`sha256` manifest schema exports all 336 Git blobs correctly. See
`evidence/2026-10-11/PACKAGE_PREFLIGHT.json`.

The source digest of upstream `TokenManager.scala` previously matched a generic
API-key heuristic. The manifest now labels each digest with a `sha256` field;
source paths, Git revision and digest values are unchanged. Gitleaks 8.30.1
reports no leaks in the staged PR; no ignore rule or scanner waiver was added.

## Physical hardware check: 2026-10-12

[The original hardware record](evidence/2026-10-12/README.md) adds evidence from
the connected Arty A7-100T; the October 11 records remain unchanged.

- Vivado 2025.1 JTAG programming succeeds on XC7A100T, startup status HIGH.
- All 17,409,032 payload bytes are written to DDR and individually read back
  before RUN; transfer/readback takes 544.1 seconds. Bitstream and payload hashes
  match the original implementation and RTL-validated software.
- Physical OpenSBI v1.9, Linux 6.6.0 and BusyBox shell boot. COW, page protection,
  FP64 process context, timer and total system-check PASS; process exit status 0.
  The intentional child SIGSEGV belongs to the passing page-protection oracle.
- Subsequent shell reads of `/proc/version` and `/proc/meminfo` succeed;
  MemTotal is 245,784 KiB. Transport restores the original 16 ms FTDI latency.

PCB revision remains unknown; this exact official E.0 MIG image works on the
connected board. 该首次启动记录不包含 Gemmini 实物回归，后续覆盖见下方新增章节。
FP16/FP32 全面检查、全 256 MiB DDR 扫描、长期稳定性和功耗仍未验证。
This first run used volatile SRAM and did not write Flash.
Treat the result as successful first bring-up, not full hardware release.

DRC retains 360 warnings; methodology retains 49 warnings and 16 advisories,
including DSP pipeline recommendations, MIG clock/reset structure, control-set
packing and a potential D-cache SDQ address collision. Reports are preserved;
severities were not downgraded and no CDC waiver was used.

The validated engineering bitstream SHA256 is
`ccc33c511e613561fb9dd1e9c847bd3b84037da1d078c44cd3de197d55dffde1`.
The corresponding 17,409,032-byte payload SHA256 is
`eb2ee34cc1a744498ac63b4e3fae425d4bb06be422ae6d41bd1ead696201134f`.
These binaries are not stored in Git. Rebuilt software may differ by compiler
and build timestamps; a new core/board toolchain requires fresh functional and
implementation checks rather than inheriting these measured results.

## Persistent Flash target: 2026-10-12

The [separate Flash archive](evidence/2026-10-12/flash/README.md) binds the new
implementation to its exact input sources and keeps the earlier records intact.
It adds a synchronous boot ROM and SPI reader, preserving the CPU, MMU, FPU,
Gemmini and original Linux payload. Routed use is 53,944 LUTs, 15,618 Slice sites,
35,645 FFs, 31 BRAM tiles and 117 DSPs. WNS/WHS are +1.276/+0.015 ns, routing
errors are zero and critical CDC/DRC guards pass. Only 232 Slice sites remain.

The identified S25FL128S was fully backed up before erase/program/verify; the
16 MiB backup stays private. Vivado reconfiguration from Flash and a subsequent
operator-confirmed loss of all power both boot OpenSBI/Linux without downloading
a bitstream or software. The cold-start observer records one USB disconnect and
five Linux checks with exit status 0. Runtime DDR/initramfs changes still vanish
on reset; the stored startup image persists. Hardware Gemmini qualification and
the other acceptance limits above remain pending.

## Linux/Gemmini 实物回归：2026-10-12

后续的新标准软件镜像完成 25,797,640 字节 DDR 完整读回（806.172 秒）、Linux 启动，
板上 15 个程序摘要与构建记录一致。五项系统检查、原 13 项 Gemmini 测试及新增
16 项 OS/WS 矩阵对照均通过；最终运行器和 watchdog 回收检查也通过。
实际用例未超时；单独构造的 1 秒 watchdog 超时按预期返回 137。

本轮使用相同已验证 UART 位流，没有增加或裁剪 RTL，也未改 Flash。
上述两个历史归档的测试范围保持原样；本轮原始测试日志、精确来源及
毫秒级计算计时见 [中文报告](evidence/2026-10-12/linux-gemmini/REPORT.md)。
多数小矩阵端到端路径比朴素 CPU 参考更慢；完整模型及其他未覆盖项目仍待验证。
