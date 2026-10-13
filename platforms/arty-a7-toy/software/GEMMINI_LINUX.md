# 当前 Linux/Gemmini 软件与验证

标准 bbkernel/rootfs 流程将 RV64 程序放入 `/root`，打包 `fw_payload.bin`，由对应 UART/Flash
组合装入 DDR；不需要独立 ELF 上传协议或 SD 卡。
直接验证用 [队友入口](../HARDWARE_TEST.md)，当前仍使用约 25.8 MB 标准镜像和 15 个程序，
覆盖 Linux 五项检查、原 13 项 Gemmini 与 16 项 OS/WS 矩阵对照。
计时包括分块、DMA、配置、同步和 CPU 累加，不代表纯 MAC 延迟。

软件验证属于 [完整 Toy/Linux 阶段](../../../history/02-toy-linux/README.md)，
[旧说明](../../../history/02-toy-linux/uart/docs/GEMMINI_LINUX.md)与旧实板结果已归档。
当前保留同一软件 ABI，旧硬件的验收结果不会随软件继承。

## 重建软件

准备脚本默认核对当前 profile，适配 DIM=8、bank 参数，保留固定参考 ISA 与比较逻辑。
在带 RV64 Linux GNU 工具链及内核构建依赖的隔离 Linux/Nix 环境执行：

```bash
python3 software/prepare_gemmini_linux.py
timeout --signal=TERM --kill-after=10s 3600s python3 -u software/build_gemmini_image.py --cache-base "$PWD/build/empty-cache" --sdk "$RV64_LINUX_SDK"
```

产物为 `build/board-software/fw_payload.bin`、`build/LINUX_GEMMINI_BUILD.json`。
重建可能改变摘要，需配自己的构建记录重新验证。Agent 构建遵循工作区 MCP 约定或本轮授权；
队友运行已发布包不需要构建。

离线核对实板结果时，从平台目录显式给对应位流摘要：

```bash
python3 scripts/verify_linux_gemmini.py --build-record <LINUX_GEMMINI_BUILD.json> --hardware-result <RESULT.json> --expected-bit-sha256 <本次位流摘要>
```

默认摘要指向当前 UART 发布；历史日志需指定旧摘要。看门狗入口为 `host/check_watchdog.py`。
模型边界见 [MODEL_COMPATIBILITY.md](MODEL_COMPATIBILITY.md)，尚无整模型验收。
