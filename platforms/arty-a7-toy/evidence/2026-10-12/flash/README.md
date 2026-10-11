# Persistent Flash boot evidence

The connected **Arty A7-100T** passed autonomous Flash boot on **2026-10-12**.
The operator then confirmed removing all power and reconnecting it. The UART
observer recorded USB loss, a fresh software CRC check, OpenSBI/Linux and five
passing system checks with process exit status 0. No application bitstream or
software was downloaded during the cold-start test.

| Measurement | Result |
|---|---:|
| FPGA / identified Flash | XC7A100T / S25FL128S, JEDEC `012018` |
| Routed LUT / occupied Slice sites | 53,944 / 15,618 (98.54% of sites) |
| FF / BRAM tiles / DSP | 35,645 / 31 / 117 |
| WNS / WHS / routing errors | +1.276 ns / +0.015 ns / 0 |
| Implementation / timeout | 1,391.1 / 3,600 seconds |
| Flash backup | All 16,777,216 bytes; not published |
| Flash program and verification | PASS, Vivado 2025.1 |
| Software image | Original 17,409,032 bytes; LZ4 3,636,031 bytes |
| Observed cold-start/check window | 135.172 seconds including operator action |
| Cold-start Linux checks | COW, protection, FP64 context, timer, overall PASS |

`implementation/` preserves the Vivado 2024.1 routed reports and build record.
`sources/` snapshots the actual implementation inputs, boot firmware and initial
host procedure; `software/` records ROM/core/payload/image hashes. The October 11
records refer to their separately preserved original sources and remain unchanged.
Only `TLROM` was replaced in the generated core; CPU, MMU, FPU, Gemmini and the
Linux payload were retained. New SPI and recovery simulations are under `tests/`.

`hardware/program.log` records the complete backup, erase/program/verify and
`boot_hw_device` request. `linux-console.log` records the first automatic boot;
`cold-boot-1.log` and its JSON record preserve the power-cycle observation.
`AUTOMATIC_BOOT_RESULT.json` records an initial monitor formatting failure:
the raw console used CRCRLF and showed all checks passing, but the monitor waited
for single-CR line endings. Only the monitors were stopped after Vivado exited.
The corrected observer, archived as `cold-observer.py`, then completed the
physical cold-start test normally. Raw logs and the interrupted monitor record
are retained; no Flash rewrite was needed.

After this measured run, the maintained Flash XDC added quiet guards for absent
synchronizers in the non-Flash configuration. The applied Flash-mode exceptions
are unchanged; the exact built XDC remains in `sources/board/flash_boot.xdc`.

JP1 is shorted and SW0 is 0 for autonomous boot. See
[`../../../FLASH_BOOT.md`](../../../FLASH_BOOT.md) for the repeatable build,
program and recovery commands. Bitstream/MCS/payload binaries and private Flash
backups are excluded from Git; `MANIFEST.json` hashes all public evidence.
PCB revision remains unconfirmed, physical Gemmini operator tests and extended
hardware qualification remain pending, and runtime RAM/initramfs edits are volatile.
