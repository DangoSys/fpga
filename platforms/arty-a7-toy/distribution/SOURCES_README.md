# 下载包对应源码与构建输入

`fpga/` 是 Release 标签所指提交的完整 Git 文件快照；构建说明、板级约束、
Chisel 覆盖、软件准备流程、测试源码与实际执行输入/证据均保留。
`SOURCE_COMMIT.txt` 记录该提交，`MANIFEST.json` 逐项绑定本源码包文件。

软件依赖的原始归档位于
`fpga/platforms/arty-a7-toy/build/downloads/`，包括固定提交的 Linux、BusyBox、
OpenSBI 与 bbkernel，原始许可证保留在各归档中。摘要与归档构建日志的 CACHE
记录一致。`actual-configs/` 保存最新 Linux/Gemmini 镜像使用的 Linux/BusyBox
配置及板级软件修改清单；实际 14 个 Gemmini C 输入另在仓库 evidence 中。

复现方法见 `fpga/platforms/arty-a7-toy/software/GEMMINI_LINUX.md`；
Flash 软件使用此前标准镜像，仅安装 `linux_system_check-linux`，流程见
`FLASH_BOOT.md`、`software/build.sh`、`scripts/build_board_firmware.py`。
硬件固定依赖由 `dependencies.json` 指定，Chisel 构建会按固定提交取回；
原许可证副本见 `notices/`。运行 Vivado 生成 IP 需要自己的合法工具安装。

本包未包含 Git 数据库、凭据、板上 Flash 原内容备份或与测试无关的运行记录。
操作步骤与日志中的命令使用原文；源码遵循各组件自己的许可证。
