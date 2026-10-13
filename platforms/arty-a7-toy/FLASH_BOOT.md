# Flash 掉电启动与恢复路线

Flash 仍有用途，`boot/`、`host/flash.py`、`host/observe_flash_boot.py` 与相关 Tcl 保留在平台。
**已验收的 Flash 产物属于阶段 02**，不是当前 ROB/PR10 UART 的固化版。

## 对应版本

旧 Flash 位流 `78d2e703…23c18` 配原约 17.4 MB Linux 镜像，已完成烧写/读回和真实断电启动。
[原记录](../../history/02-toy-linux/flash/2026-10-12/README.md)与
[机器结果](../../history/02-toy-linux/flash/2026-10-12/FLASH_RESULT.json)移入对应阶段。
使用 [2026-10-12 Release](https://github.com/DangoSys/fpga/releases/tag/arty-a7-toy-2026-10-12)
的 Flash 组合，不能混配当前 UART 位流、旧 MCS 和新软件。

- JP1 短接、SW0=0：SPI 配置 FPGA，Boot ROM 从 Flash 解压到 DDR，进入 OpenSBI/Linux。
- SW0=1 后 BTN0：UART 恢复；运行时 DDR 与 initramfs 修改仍会掉电丢失。
- 当前 ROB/PR10 未重新完成 Flash 实现与冷启动验收。

## 保留的构建与操作入口

在隔离 Linux 环境先生成寄存器 ROB 配置及原软件，再构建 Flash 目标：

```bash
python3 -m pip install -r boot/requirements.txt
bash boot/build.sh
python3 scripts/prepare_flash_boot.py --payload build/board-software/fw_payload.bin --boot-bin build/flash-boot/boot.bin
python3 scripts/start_board_build.py --flash
```

烧写用 `board/make_flash_image.tcl`、`board/program_flash.tcl` 或 `host/flash.py`。
按实物确认 Flash 料号，擦写前完整备份 16 MiB，备份保留本地。
具体参数、分区与 CRC 见 [原流程快照](../../history/02-toy-linux/flash/docs/FLASH_BOOT.md)。
烧写/verify 完成后，以 `host/observe_flash_boot.py --require-disconnect` 观察真实断电重接，
确认全部电源移除后无需重新配置/加载仍可取得 Linux 检查结果。
新组合必须独立保存实现、镜像、烧写与冷启动证据，不能继承旧结论。
