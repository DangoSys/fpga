# Full-system adaptation contract

The original Pebble CPU and all ten operators are mandatory. Disabling MMU,
FPU, caches, Linux, or operators is not an acceptable way to pass implementation.
Cache/bank capacities and concurrency may be sized for the FPGA. Document such
choices and validate software behavior; preserve the complete functionality.

## Hardware boundary

The generated `PebbleLinuxChip` exposes AXI DDR and AXI peripheral masters plus
one PLIC interrupt input. It retains CLINT, the original L2 and scratchpad.
The device tree marks scratchpad disabled for Linux memory discovery, matching
the original `WithMbusScratchpad`; software can still access it explicitly.

The board implementation must hold the CPU reset until DDR calibration and
payload upload both finish. Reset release must be synchronized separately in
each clock domain. An AXI clock converter must bridge the 50 MHz core to the
MIG UI clock; simply wiring the clocks together is invalid.

The unmodified official MIG preset has 128-bit AXI, 4-bit IDs, a 28-bit local
address, and narrow bursts disabled. Integration must validate/handle narrow
uncached CPU and DMA transfers, remove only the `0x80000000` DDR base, preserve
AXI response ordering, and reject addresses outside the 256 MiB window.

## Software contract

`SOFTWARE_BASELINE.json` pins the upstream Linux/OpenSBI/BusyBox/bbkernel
revisions. The original Linux BootROM enters OpenSBI at `0x80000000` with
`a0=mhartid` and `a1=DTB`. The image must be loaded before releasing the CPU.
The original OpenSBI platform stages its writable DTB at `0x88000000`; reserve
that area during loading, and preserve it until OpenSBI hands off to Linux.

The original SCU UART is hart 0 TX `0x60020000`, RX `0x60020004`, and status
`0x60020005` (bit 0 means RX valid). OpenSBI TX does not poll readiness:
the physical bridge must backpressure writes until accepted, never discard
characters when the UART is busy. The old bare-metal UART map is incompatible.
Implement shutdown/reset reporting at `0x60000000` as physical board control,
not a DPI stub.

The generated CLINT/DTB timebase is 1 MHz. The upstream bbkernel OpenSBI
platform hardcodes 10 MHz; its FPGA adapter must use the actual 1 MHz value
or read the DTB. A boot banner alone does not verify timer correctness.
`software/prepare_platform.py` applies the 1 MHz setting and changes the
upstream `mem=512M` command line to `mem=256M`, preserving SBI/RoCC support.

## Release acceptance

1. Source/configuration audit; no accidental opcode reassignment or feature loss.
2. Real resource fit including DDR, loader and peripherals; no unresolved cells.
3. AXI backpressure, burst/narrow access, reset and DDR calibration simulations.
4. OpenSBI, Linux boot, interactive shell, timer and PLIC operation.
5. User-process Sv39/page-fault checks, floating-point tests and all ten operators.
6. Routed timing, DRC/CDC/I/O checks, then cold boot on the confirmed PCB revision.

Current progress and resource results belong in README/evidence. Uncompleted
items above must not be reported as passing.
