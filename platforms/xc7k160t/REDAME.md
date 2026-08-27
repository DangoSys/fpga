# xc7k160t Platform

Vivado build flow for mapping buckyball (`DigitalTop`, config
`sims.p2e.P2EPebbleLinuxConfig`) onto the Xilinx Kintex-7 **xc7k160tffg676-2**.

## Contents

| File | Purpose |
|---|---|
| `build.tcl` | Batch flow: synthesis → place & route → bitstream, plus utilization / timing / power reports |
| `dpi_stubs.sv` | Synthesis stubs for Verilator-only DPI trace modules (`CTraceDPI`, `ITraceDPI`, …) and `plusarg_reader` |

## Prerequisites

- Vivado (tested with **2024.1**)
- The buckyball submodule fetched: `git submodule update --init`
- Generated RTL at `thirdparty/buckyball/arch/build/sims.p2e.P2EPebbleLinuxConfig/`.
  Generate it first (from the buckyball repo root):

  ```bash
  cd fpga/thirdarty/buckyball
  nix develop
  bbdev bebop-p2e --verilog "--config sims.p2e.P2EPebbleLinuxConfig"
  cd ..
  cd ..
  cd platforms/xc7k160t
  vivado -mode batch -source build.tcl
