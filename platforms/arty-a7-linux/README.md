# Full Pebble on Arty A7-100T — work in progress

This target ports the complete Pebble functionality at Buckyball
`1f3d54535bd5fb76d5fd2f6b05ed36e591cf3097`. It is **not yet a board release**.
The existing `../arty-a7` target is a reduced bare-metal demonstration; its
successful board test does not establish Linux support.

## Preserved functionality

`scripts/resolve_config.py` reads the pinned original TOMLs and supplies the
upstream Scala parameter readers. It retains the original ISA registrations,
not just operator implementations:

- Rocket RV64 with Sv39 virtual memory, supervisor/user modes, FPU
  (`minFLen=16`, `fLen=64`), Zba/Zbb/Zbs, multiplier/divider and BTB.
- I-cache, D-cache, inclusive L2 and scratchpad at `0x08000000`. The first
  diagnostic baseline uses the original 32/8/512/64 KiB capacities; these
  capacities are FPGA configuration choices, not required ISA features.
- All 10 original operators: Transpose, SMatMul 8×16, Im2col, ToInt8, Int2Fp,
  LUT, MaxPool, Int8Add (including ReLU), Int8Mul, and MatAdd.
- Original 24×64×128-bit private banks, DMA, accelerator TLB and frontend.
- CLINT timer/software interrupts, PLIC, and an external interrupt input.

Board adaptations use a 50 MHz core clock and a 256 MiB DDR address window
at `0x80000000`. ASIC clock gates become FPGA clock enables. Simulation DPI
tracing is disabled. CPU and accelerator source files remain byte-identical
to `UPSTREAM_MANIFEST.json`; none are hand-rewritten as Verilog.

## Build and resource gate

Use Linux with Python 3.11+ (or Python 3.10 with `tomli`), sbt, and Vivado
with Artix-7 support:

```sh
bash scripts/elaborate.sh --repository /path/to/buckyball
vivado -mode batch -source synth_core.tcl
```

`generated/PebbleLinuxChip.sv` is Chisel-generated. Reports and checkpoint
are under `build/synth/`. This is an out-of-context measurement of the full
core; external DDR/peripherals are not black-box substitutes for core logic.

`python3 scripts/resource_fit.py` compares the measured core and official MIG
reports against the device capacity. Its summed OOC figures are an estimate,
not a substitute for complete board implementation.

Generate and measure the official MIG separately before running the resource
gate (`resource_fit.py` exits 2 when the core exceeds the device):

```sh
vivado -mode batch -source board/create_mig.tcl
vivado -mode batch -source board/synth_mig.tcl
python3 scripts/resource_fit.py
```

## FPGA memory binding

The optional CIRCT memory-macro path leaves CPU/operator RTL intact and supplies
board-specific synchronous RAM modules. Large data arrays use block RAM; small
cache tags use distributed RAM. Only single read/write-port macros are supported;
unrecognized shapes are rejected. Disabled/write-cycle read outputs hold their
previous value where the original memory contract leaves them undefined.

After preparing sources and generating the baseline above:

```sh
sbt -Dsbt.override.build.repos=true -Dsbt.repository.config=project/repositories \
  -batch 'runMain fpga.arty.linux.EmitPebbleLinux build/fpga-memory --fpga-memories'
python3 scripts/prepare_fpga_memories.py build/fpga-memory/PebbleLinuxChip.sv \
  --output-dir build/fpga-memory/bound
python3 tests/check_fpga_memories.py --original generated/PebbleLinuxChip.sv \
  --bound build/fpga-memory/bound
vivado -mode batch -source board/check_memory_mapping.tcl
```

The comparison test requires Icarus Verilog (`iverilog`/`vvp`). It checks all
10 memory types (45 instantiated memories) against the actual original generated
RTL and a separate scoreboard, covering all addresses, write masks, enables and
read latency. The 4 KiB D-cache array maps to 4 BRAM tiles, 2 LUT and 0 FF in its
standalone synthesis. Whole-chip synthesis with this binding remains pending.

## Linux software

With Python 3.12+, `riscv64-unknown-linux-gnu-gcc`, CMake, Make and the standard
Linux kernel build dependencies (including flex, bison and development headers):

```sh
bash software/build.sh
```

This prepares pinned bbkernel/Linux/OpenSBI/BusyBox sources under `build/software/`.
Only the board memory limit (256 MiB) and CLINT frequency (1 MHz) are patched in
bbkernel. `linux_system_check.c` checks process isolation, page protection, FP64
context and scheduled timer wakeup. A host test or successful compilation does
not prove an FPGA boot. All operator regression binaries remain required.

The OpenSBI/Linux/BusyBox payload build passed. Its hash is recorded in
`VALIDATION.json`; the payload and downloaded dependencies are not committed.

## Required before programming

Still required: resource fit, board-revision validation for DDR, physical
MIG/AXI integration, UART/SCU bridge, payload loading, OpenSBI + Linux +
rootfs, VM/FPU/operator tests, routed timing/DRC, and physical boot evidence.
The core checkpoint alone must never be presented as a working Linux chip.
Fit the caches and memory implementation to the A7-100T while preserving
CPU/MMU/FPU/Linux and all operator functionality. Record every capacity and
bandwidth change, and validate its software-visible effects.

## Diagnostic baseline (not an A7 resource requirement)

The original-capacity core with default behavioral memory lowering synthesized
to 195,371 Slice LUTs (including 84,607 LUT6 primitives), 113,625 FF, 144 BRAM
tiles and 38 DSP. It exceeds this device;
there is no routed bitstream from that build. D-cache alone mapped to 30,181
LUT and 68,023 FF with no BRAM. The private accelerator backend used 56,602
LUT, including 6,144 LUT RAM. Hierarchical numbers include descendants and
must not be summed across parent/child rows.

`evidence/2026-10-10/` contains the original utilization/DRC reports and memory
test output. These baseline figures are not a lower bound on the resources
needed for complete functionality. Run `python3 -m unittest discover -s tests`,
`python3 scripts/audit_sources.py` and `python3 scripts/audit_elaboration.py`
to verify the original configuration, source hashes and elaborated features.
