# FPGA

This repo is where we put [Buckyball](https://github.com/DangoSys/buckyball) onto FPGA boards.

## Platforms

| Platform | Target | Build guide |
|---|---|---|
| Kintex-7 | `xc7k160tffg676-2` | [Existing P2E flow](platforms/xc7k160t/README.md) |
| Digilent Arty A7-100T | `xc7a100tcsg324-1` | [Standalone CPU/BRAM/UART platform](platforms/arty-a7/README.md) |
| Digilent Arty A7-100T, Toy/Linux | `xc7a100tcsg324-1` | [CPU/Sv39/FPU/Gemmini 8×8 with DDR](platforms/arty-a7-toy/README.md) |

The Arty A7 platforms have their own pinned Chisel build, serial loader, firmware,
constraints and verification record. Follow its guide directly; the setup and
demo below describe the existing Kintex-7 flow.

### Arty A7-100T 队友实板入口

Windows 克隆后进入 `platforms/arty-a7-toy`，安装
`python -m pip install -r host/requirements-hardware.txt`，再执行：

```powershell
.\run_hardware.ps1 -Port COM5 -Vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat'
```

入口自动下载固定 ROB/PR10 工程预发布、核验摘要，再复用原 Linux/Gemmini 验证器。
无需重建位流或 Linux；没有接板可加 `-PrepareOnly`。
请先阅读[中文准备与日志说明](platforms/arty-a7-toy/HARDWARE_TEST.md)。

The Toy/Linux target passes complete board implementation, Linux RTL checks and
a physical Arty A7-100T boot with full image readback and five Linux checks.
Its PCB revision remains unconfirmed and physical Gemmini testing is pending;
see [the hardware record](platforms/arty-a7-toy/evidence/2026-10-12/README.md)
and its build/programming guide before using another board.

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
