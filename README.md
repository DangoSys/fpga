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

Arty A7-100T 的 Toy/Linux 已验证位流、配套软件与烧录脚本可直接下载：
[中文下载与使用说明](platforms/arty-a7-toy/DOWNLOADS.md)。
提供临时 UART 加载、Flash 掉电启动两套包，另附对应源码和 SHA256 校验值。

The Toy/Linux target passes complete board implementation, Linux RTL checks and
a physical Arty A7-100T boot with full image readback and five Linux checks.
PCB 修订号仍未确认；最新临时镜像已通过 Linux/Gemmini 实物回归，完整模型等仍未验收。
详见 [中文测试报告](platforms/arty-a7-toy/evidence/2026-10-12/linux-gemmini/REPORT.md)
及对应构建/烧录指南，不能直接认定其他板卡也已验证。

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
