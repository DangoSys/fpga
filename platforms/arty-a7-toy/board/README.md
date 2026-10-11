# Board integration

Build and programming commands are in [the platform guide](../README.md).
This directory targets Arty A7-100T `xc7a100tcsg324-1` with official Digilent
Rev E.0 DDR parameters. The recorded hardware run passes full payload DDR
readback and Linux checks; physical PCB revision remains unconfirmed.

- `toy_a7_top.sv`: 100 MHz input, MMCM/BUFG clocks, per-domain reset sequencing,
  physical UART/LED/DDR pins, actual MIG and AXI Clock Converter instances.
- `toy_a7_platform.sv`: validated Chisel core, loader/CPU DDR arbitration,
  fullwidth memory adapter and SCU console. CPU remains reset until verified RUN.
- `axi_fullwidth.sv`: preserves lanes, strobes, IDs and backpressure while
  translating narrow INCR/FIXED beats into aligned 128-bit DDR accesses.
- `ddr_uart_loader.sv` / `loader_axi.sv`: CRC-framed load, readback and release;
  acknowledgements wait for DDR responses. INFO bytes preserve LUTRAM inference.
- `axi_scu.sv`: UART/exit MMIO and 256-byte RX FIFO, with accepted-response pops.
- `arty_a7.xdc`: actual pins and targeted asynchronous I/O/reset exceptions;
  DDR data/address/control and internal CPU timing remain checked.
- `build_board.tcl`: complete IP generation, synthesis, placement, routing and
  bitstream. Setup/hold, CDC Critical, bus skew, routing errors and DRC errors
  stop the build. No warning severity downgrade or CDC waiver is applied.
- `program_arty.tcl`: explicit volatile JTAG programming; exactly one target
  and one XC7A100T required. The platform's `../program.tcl` entry delegates here.
  The exact script used for first bring-up is also archived with the hardware logs.

`vendor/` contains unmodified pinned Digilent MIG/board inputs and their license.
Vivado generates proprietary vendor IP into ignored build directories locally.
