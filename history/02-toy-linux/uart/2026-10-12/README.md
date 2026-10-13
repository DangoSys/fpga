# First physical Toy/Linux bring-up

The Arty A7-100T was programmed on **2026-10-12, Asia/Shanghai**, using the
engineering image from [PR #5](https://github.com/DangoSys/fpga/pull/5), commit
`257b632a533dd98a7c526870edbd21c5a6976d09`. The PCB revision remains unknown;
MIG uses the pinned official Digilent E.0 parameters.

| Recorded hardware run | Result |
|---|---|
| FPGA / programming tool | XC7A100T / Vivado 2025.1 |
| JTAG / serial | `210319BCC5FCA` / COM5, 1 Mbps |
| Programming | PASS, startup status HIGH, volatile SRAM |
| Complete DDR image readback | 17,409,032 bytes, all equal, 544.1 seconds |
| Software | OpenSBI v1.9, Linux 6.6.0, BusyBox shell |
| Linux checks / exit status | Five PASS markers / 0 |
| Timer check | `elapsed_ns=103836000` |
| Live shell MemTotal | 245,784 KiB |
| Load, boot and checks | 577.922 seconds |

## Logs and provenance

[`hardware/MANIFEST.json`](hardware/MANIFEST.json) hashes every original artifact;
[`HARDWARE_RESULT.json`](hardware/HARDWARE_RESULT.json) records the outcome and
coverage. Files retain their original bytes, timestamps in logs and experiment
paths. These paths are provenance, not prerequisites for a new checkout.

- [`program.log`](hardware/program.log), [`program.jou`](hardware/program.jou),
  [`PROGRAM_RESULT.json`](hardware/PROGRAM_RESULT.json): JTAG device selection,
  programming and startup state. The exact used
  [`program_arty.tcl`](hardware/program_arty.tcl) is archived alongside them.
- [`load-and-linux.log`](hardware/load-and-linux.log): complete write/readback
  progress, verified RUN, boot and Linux checks.
- [`linux-console.log`](hardware/linux-console.log): original serial bytes;
  PASS for COW, page protection, FP64 process context, timer and total check.
- [`live-console-first.log`](hardware/live-console-first.log): process exit
  status 0, then an unsuccessful auxiliary probe because `uname`/`grep` links
  are absent in the minimal rootfs. [`live-console.log`](hardware/live-console.log)
  confirms the kernel, memory and interactive shell using shell builtins.
- Archived Python files and `dfx_runtime.txt` preserve the actual procedure.
  The D2XX transport uses the existing host loader unchanged, opens only UART B,
  temporarily sets latency from 16 to 2 ms, then restores 16 ms. No registry or
  EEPROM change is made. These archived scripts include local paths; use the
  maintained platform entry points for a new run.

The page-protection test deliberately triggers a child SIGSEGV. Its parent
checks the fault and prints PASS; that trace is expected.

## Repeat programming and boot

Use [`../../program.tcl`](../../program.tcl), which resolves and delegates to
[`../../board/program_arty.tcl`](../../board/program_arty.tcl). From any directory:

```bash
vivado -mode batch -source /absolute/path/to/platforms/arty-a7-toy/program.tcl \
  -tclargs /absolute/path/to/toy_a7.bit
```

The script requires one attached JTAG target and one XC7A100T. On Windows the
equivalent wrapper is `program.ps1 -Bitstream <path> -VivadoBin <Vivado-bin>`.
After programming, press BTN0, wait for DDR readiness/LED0, close other serial
clients and load the software from the platform directory:

```bash
python host/load.py --port COM5 --check-linux build/board-software/fw_payload.bin
python -m serial.tools.miniterm COM5 1000000 --eol LF
```

Choose the actual port. Build products are not committed; follow the platform
build guide to create the `.bit` and payload. The measured files are identified by:

- Bitstream SHA256: `ccc33c511e613561fb9dd1e9c847bd3b84037da1d078c44cd3de197d55dffde1`.
- Payload SHA256: `eb2ee34cc1a744498ac63b4e3fae425d4bb06be422ae6d41bd1ead696201134f`.

Programming and DDR contents are volatile; repeat both steps after power loss.
PCB revision identification, physical Gemmini tests, exhaustive FP16/FP32 checks,
full DDR sweep, long-duration stability and power measurements remain pending.
The prior 98.82% Slice utilization and warning/coverage limits still apply.
