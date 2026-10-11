# Toy/Linux on Arty A7-100T

A Chisel-generated Toy platform for `xc7a100tcsg324-1`, with CPU, Sv39, full
FP16/32/64 support and Gemmini 8×8. Complete board implementation, timing, CDC
checks and Linux RTL tests pass. The physical board revision is unconfirmed:
this is a **Rev E engineering bring-up target**, awaiting hardware DDR and Linux
acceptance. See [measured results](VALIDATION.md) before programming.

## Architecture and scope

- RV64IMAFDC with Zfh/Zba/Zbb/Zbs, M/S/U, PMP, Sv39, interrupts and 8 KiB I/D
  caches. FP16/32/64 share the FMA; the register file uses validated LUTRAM.
- Gemmini 8×8 OS/WS, 64 DSP PE MACs, 64 KiB accelerator SRAM and 23 opcodes.
  Group-query ownership, simultaneous SubROB enqueue/retirement, WS bias and
  rounding fixes are included as Chisel overrides.
- 256 MiB DDR3L at `0x80000000`, official Digilent Rev E MIG, real Xilinx AXI
  Clock Converter and a byte-strobe preserving fullwidth DDR adapter.
- 100 MHz oscillator, 25 MHz CPU, 83.33 MHz MIG UI, 500 kHz CLINT; UART 1 Mbps
  8N1. SCU exit/TX/RX/status: `0x60000000`, `0x60020000/04/05`.

This is the previously evaluated FPGA profile, not the default full-size Toy:
other Balls, L2, BTB, debug, extra performance counters and the separate TL
scratchpad are absent; broadcast coherence and basic counters remain. Accelerator
SRAM is distinct from that removed TL scratchpad. No software emulation is
silently substituted. The current PR adds no further core cuts.

Pinned upstream files are restored into ignored `upstream/`; dependencies into
ignored `thirdparty/`. `patches/` contains the hardware overrides, `src/` the
top/configuration, `rtl/` memory/RF adapters, `board/` physical integration,
`software/` pinned Linux/OpenSBI preparation, and `tests/` independent oracles.

## Build

Run from this directory on Linux with Python 3.12+, Git, curl, JDK 17, sbt,
firtool 1.62.1, RV64 bare-metal and Linux GCC/binutils, Verilator, Icarus Verilog,
and Vivado with Artix-7 support. Kernel builds also need CMake, Make, flex,
bison and the standard kernel development libraries. The tested tool versions
and byte hashes are recorded in `evidence/2026-10-11/`.

```bash
cd platforms/arty-a7-toy
# Optional --repository reuses pinned Git objects without changing that checkout.
bash scripts/elaborate.sh --repository ../../thirdparty/buckyball
bash scripts/build_test_programs.sh
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/run_board_regression.py
python3 scripts/start_board_build.py
```

Omit `--repository` to fetch a private pinned Git cache. Chisel 6.7.0 and Scala
2.13.16 are set by `build.sbt`; sbt is pinned in `project/build.properties`.
Set `CHISEL_FIRTOOL_PATH` to the directory containing firtool when required.
`scripts/verify_target.py --core` rejects a regenerated core or SRAM/RF binding
whose bytes differ from the validated version.

The board launcher returns immediately with a fresh output directory. Inspect
its `RUN.json`, `phase.txt` and `vivado.log` until status is `COMPLETED`, exit code
0 and `bitstream_generated` true. The entire Vivado process group has a
3,600-second timeout plus 15-second termination grace. Timing, CDC, bus-skew,
routing and DRC failures prevent bitstream generation. `VIVADO` may point to an
installed compatibility wrapper; otherwise `vivado` is resolved on PATH.

```bash
bash software/build.sh
python3 scripts/build_board_firmware.py
timeout --signal=TERM --kill-after=15s 3600s python3 scripts/check_board_linux.py
timeout --signal=TERM --kill-after=15s 1800s python3 scripts/check_board_uart_boot.py
python3 scripts/check_board_cdc.py board-YYYYMMDD-HHMMSS --output-name board-cdc-new
```

Use the actual board run name for CDC testing and a fresh simulation output
name. OpenSBI rebuild defaults to `riscv64-linux-gnu-`; `--cross-compile` selects
another compatible GNU prefix. `--software-base` can reuse another isolated root
containing `build/software` produced by the same pinned software flow.

Generated RTL, firmware, dependencies, checkpoints and bitstreams are build
products and are not committed. A successful fresh board run produces
`build/board-<timestamp>/toy_a7.bit`; the Linux payload is
`build/board-software/fw_payload.bin`.

## First hardware boot

1. Confirm the physical DDR/revision matches the official Rev E parameters;
   connect PROG/UART USB and select the single XC7A100T in Hardware Manager.
2. Program the selected `.bit` into volatile FPGA SRAM. On Windows:
   `./program.ps1 -Bitstream <absolute-bitstream-path> -VivadoBin <Vivado-bin>`.
   The script does not write flash and is not run automatically.
3. Press BTN0, wait for LED0 (DDR calibrated), and close other serial clients.
4. Install `pyserial`, then load and byte-verify the image before releasing CPU:

```bash
python host/load.py --port COM5 --check-linux build/board-software/fw_payload.bin
```

Use the actual serial port. Expect OpenSBI, Linux, BusyBox and five PASS markers
for COW, page protection, FP64 process context, the timer and the total Linux
system check. A 17 MiB transfer with full readback takes several minutes at
1 Mbps. After the script closes the port, an interactive console is available
with `python -m serial.tools.miniterm COM5 1000000 --eol LF`.

LED1 indicates loader error or nonzero exit, LED2 CPU released, LED3 heartbeat.
LEDs alone do not establish software success. Preserve the console transcript
and DDR calibration result; operator acceptance additionally needs Gemmini tests.
