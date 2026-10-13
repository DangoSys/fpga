# Persistent Toy/Linux boot

This target keeps the validated CPU, Sv39, FPU, Gemmini 8x8 and original Linux
payload. A new boot ROM reads the onboard SPI Flash, bounds-checks and decompresses
an LZ4 block into DDR, checks its CRC32, and enters the original OpenSBI image.
Runtime DDR and changes to the initramfs remain volatile; the stored boot image
survives power loss. The existing UART load/RUN path remains available for recovery.

On 2026-10-12 the connected Arty A7-100T passed Flash programming/readback
verification, autonomous Linux startup, and a physical power cycle confirmed by
the operator. Both boots passed all five Linux system checks with exit status 0.
See [the recorded implementation and hardware evidence](evidence/2026-10-12/flash/README.md).

## Layout and switches

The Arty A7-100T has a 16 MiB Flash. Configuration starts at `0x000000`, with a
4 MiB reserved partition; a 32-byte header and compressed software start at
`0x400000`, with 12 MiB available. The original 17,409,032-byte payload compresses
to 3,636,031 bytes with the pinned LZ4 version. Packing fails on overlap/overflow.

- JP1/MODE: install the shorting cap for SPI power-on configuration.
- SW0=0: automatic Flash boot after DDR calibration.
- SW0=1, then BTN0: UART recovery; load a payload using `host/load.py` as before.
- PROG reloads FPGA configuration; BTN0 resets DDR/CPU and repeats software boot.

The SPI byte engine uses 3.125 MHz mode 0 and STARTUPE2 for the dedicated CCLK pin.
The CPU reads JEDEC ID before the software header. Invalid IDs, header CRC, lengths,
LZ4 offsets or payload CRC halt in ROM and print `FAIL FLASH_BOOT`.

## Build

From this platform directory in the isolated Linux toolchain, first produce the
normal validated `build/serial-bound/` core and original board software. Then:

```bash
python3 -m pip install -r boot/requirements.txt
bash boot/build.sh
python3 scripts/prepare_flash_boot.py \
  --payload build/board-software/fw_payload.bin \
  --boot-bin build/flash-boot/boot.bin
VIVADO=/path/to/vivado python3 scripts/start_board_build.py --flash
```

The packer replaces only `TLROM` in a separate generated file. It preserves the
original device tree at `0x11000` and verifies every byte outside that module.
The ROM is an 8 KiB synchronous BRAM with a response held under TileLink stalls.
The FPGA build keeps the one-hour timeout and rejects timing, routing, critical
CDC and DRC failures. The historical October 11 results describe the archived
pre-Flash board sources, rather than certifying this changed target.

## Program

Identify the actual Flash part using the board marking/JEDEC ID and a compatible
Vivado configuration-memory entry. Do not infer the Flash variant from FPGA size.
For an identified S25FL128S with the corresponding sector variant, for example:

```bash
vivado -mode batch -source board/make_flash_image.tcl -tclargs \
  build/board-<run>/toy_a7.bit build/flash-boot/flash_payload.bin build/toy_flash.mcs
vivado -mode batch -source board/program_flash.tcl -tclargs \
  build/toy_flash.mcs s25fl128sxxxxxx0-spi-x1_x2_x4 build/flash-backup-<run>.bin
```

Programming first reads all 16 MiB into a fresh backup, then erases/programs the
image addresses and verifies Flash. It finally requests configuration from Flash
using `boot_hw_device`; it does not download the application `.bit` at that step.

`host/flash.py` wraps both Tcl steps with a one-hour timeout, records hashes and
captures UART while programming, then runs the Linux check. Example on Windows:

```powershell
python host/flash.py --vivado D:/Xilinx/2025.1/Vivado/bin/vivado.bat `
  --bitstream build/board-<run>/toy_a7.bit --payload build/flash-boot/flash_payload.bin `
  --part s25fl128sxxxxxx0-spi-x1_x2_x4 --port COM5
```

If the programming machine has hardware support but lacks Artix-7 build files,
create the MCS on the build machine with `scripts/make_flash_image.py` and copy
both the MCS and its `.mcs.json` sidecar. Add `--mcs build/toy_flash.mcs` to the
host command. It verifies the bitstream, software and MCS hashes against the
sidecar before programming. Keep Flash backups private and outside Git.

## Verify

Capture UART at 1 Mbps, 8N1. Require `PASS FLASH_PAYLOAD_CRC`, OpenSBI, the Linux
shell, and all five checks from `/root/linux_system_check-linux` with exit status
0. Finally disconnect every power source, reconnect, and repeat these checks
without running JTAG programming or `host/load.py`. A JTAG PROGRAM restart alone
does not constitute the final cold-power-cycle test.

Arm a reconnecting UART observer before disconnecting USB and any external
power supply:

```bash
python host/observe_flash_boot.py --port COM5 --require-disconnect \
  --transcript build/cold-boot.log --timeout 600
```

USB disappearance is recorded; the person performing the test must also confirm
that all board power was removed. The observer sends only the Linux system check,
never a payload or configuration file.

Allow roughly two minutes for the boot-ROM decompression and Linux startup on
the measured 25 MHz target. Do not interrupt Flash erase/program/verify; begin
the power-cycle test only after the programming command completes successfully.

`scripts/check_flash_boot.py` tests the real CPU/ROM/SPI path from empty DDR with
the original CPU oracle plus two corrupted images. Its DDR/Flash models do not
validate physical Flash or the DDR PHY. Hardware results are recorded separately.
