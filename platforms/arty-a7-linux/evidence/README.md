# Pebble resource and memory-binding evidence

`2026-10-10/` records Vivado 2024.1 results for `xc7a100tcsg324-1`.
`SHA256.json` preserves the exact report bytes; `VALIDATION.json` at the
platform root summarizes the checked source and generated-RTL hashes.

- `core-*`: original-capacity, behavioral-memory, out-of-context core run.
  Synthesis completed, but utilization exceeds the device and DRC contains
  resource errors. The timing report is pre-route, not timing closure.
- `mig-utilization.rpt`: independently synthesized official DDR controller.
- `dcache-array-utilization.rpt`: one 128x256-bit D-cache memory macro with
  the FPGA binding. This is not a new whole-chip utilization result.
- `memory-test.txt`: original-generated-RTL/scoreboard checks for all ten
  memory shapes; `MEMORY_MANIFEST.json` identifies the 45 memory instances.
- `host-linux-check.txt`: the Linux acceptance program run on the build host.
  It validates the workload itself, not a RISC-V FPGA Linux boot.

There is no full-system bitstream, routed implementation or physical Linux
boot evidence in this directory. Large generated RTL/checkpoints and the
OpenSBI/Linux payload remain build artifacts rather than repository sources.
