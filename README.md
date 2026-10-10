# FPGA

This repo is where we put [Buckyball](https://github.com/DangoSys/buckyball) onto FPGA boards.

## Platforms

| Platform | Target | Build guide |
|---|---|---|
| Kintex-7 | `xc7k160tffg676-2` | [Existing P2E flow](platforms/xc7k160t/README.md) |
| Digilent Arty A7-100T | `xc7a100tcsg324-1` | [Standalone CPU/BRAM/UART platform](platforms/arty-a7/README.md) |
| Arty A7 full Pebble/Linux (in progress) | `xc7a100tcsg324-1` | [Full configuration and resource gate](platforms/arty-a7-linux/README.md) |

The Arty A7 platform has its own pinned Chisel build, serial loader, firmware,
constraints and verification record. Follow its guide directly; the setup and
demo below describe the existing Kintex-7 flow.

## Kintex-7 setup

First, build the repository with these steps:

```bash
git clone https://github.com/DangoSys/fpga.git
cd fpga
git submodule update --init
cd thirdparty/buckyball
./scripts/nix/build-all.sh
```

After the first install, we need do `nix develop` each time from the Buckyball directory to get environment.

# Demo

The demo on this board is Pebble with a Linux boot ROM.  We have been running this with Vivado 2024.1.

```bash
cd thirdparty/buckyball
nix develop
bbdev bebop-p2e --verilog "--chip pebble"
```

Then leave that shell, go to the platform directory, and run the batch flow. It reads every `.sv` in the generated directory, stubs out the Verilator-only DPI and plusarg modules so synthesis does not choke on them, synthesizes `DigitalTop`, and continues through place, route, and bitstream. Utilization, timing, and power reports are written next to the `.bit` file.

```bash
cd platforms/xc7k160t
vivado -mode batch -source build.tcl
```

`build.tcl` will pick up `platforms/constraints/pin.xdc` when that file exists. Until it does, Vivado still runs, but there is no board pin mapping. Details that are specific to this Kintex-7 part live in `platforms/xc7k160t/README.md`.
