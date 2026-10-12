# 8×8 Gemmini 的 Linux 实物验证与复现

本轮沿用项目的标准软件镜像流程：交叉编译 Linux workload，将可执行文件安装进
rootfs 的 `/root`，生成 `fw_payload.bin`，再通过既有板级启动方式加载。
不依赖工作台的独立 ELF 上传协议，也不要求 SD 卡。

本次归档为 [`evidence/2026-10-12/linux-gemmini/`](../evidence/2026-10-12/linux-gemmini/README.md)，
包含源码索引、实际编译输入、Tcl、两次完整回归、DDR/Linux 启动片段、计时和摘要。
本机路径和串口号均需替换为复现机器上的真实位置。

## 测试内容

- 原版 13 项 Gemmini 测试仅将 `DIM=16` 适配为 `8`，ISA、比较逻辑和原始参考源码不变。
- 新增 `gemmini_linux_check-linux`：OS/WS 交替运行两轮；覆盖 8×8×8、16×16×16、
  M13/N11/K17 尾块及 M8/N24/K8；逐元素比较独立 CPU 参考结果，共 16 项。
- 大矩阵由软件拆成 8×8 子块，尾块补零；K 方向的部分结果由 CPU 累加。
  因此通过本测试不能宣称硬件 CISC 的跨 K 分块累加已通过。
- 输出 CPU 耗时和加速器端到端耗时；后者包含分块、搬运、配置、同步及 CPU 累加。
  小矩阵不保证加速，不把主机仿真耗时当作 FPGA 性能。
- 沿用原 `bb_dma_touch_mvout`，显式写入输出缓冲区，避免 Linux 零页/COW 与 DMA 的问题。
  每项新测试设 60 秒 alarm；主机运行器仍需设置独立超时。

## 准备与构建

`prepare_gemmini_linux.py` 只准备源码：核验固定参考摘要和实际 8×8/64-bit bank 配置，
生成参数、23 项 Gemmini 指令定义及 CMake 输入。构建代理须走 `bbdev_*` MCP，
并轮询任务状态；若工具不可用，应先恢复入口或取得本轮直接构建的明确授权。

供人工执行的隔离 Linux/Nix 构建示例：

完整镜像构建需要 Python 3.12+、CMake 3.22+、Make、curl、flex、bison、bc、
OpenSSL 开发库和带静态 libc/libm 的 RV64 Linux GNU 工具链。
本次实际 GCC 15.3.0、Binutils 2.46，`rv64gc/lp64d`、`-O2 -static`。
`RV64_LINUX_SDK` 指向工具链根目录，其 `bin/` 须有 `riscv64-unknown-linux-gnu-*`。
在干净平台目录执行下面的完整入口可依次编译、安装、构建 rootfs/Linux 和重打包 OpenSBI：

```bash
timeout --signal=TERM --kill-after=10s 3600s python3 -u software/build_gemmini_image.py --cache-base "$PWD/build/empty-cache" --sdk "$RV64_LINUX_SDK"
```

缓存目录可以为空；原准备流程会下载固定提交的依赖。结果为
`build/board-software/fw_payload.bin` 和 `build/LINUX_GEMMINI_BUILD.json`。
只准备/单独交叉编译时可用下面的步骤：

```bash
python3 software/prepare_gemmini_linux.py
cmake -S build/linux-gemmini -B build/linux-gemmini-build \
  -DCMAKE_C_COMPILER=riscv64-unknown-linux-gnu-gcc
cmake --build build/linux-gemmini-build -j8
cmake --install build/linux-gemmini-build \
  --prefix "$PWD/build/software/bb-tests/output/workloads"
# 然后由既有 bbkernel 流程重新生成带这些文件的 Linux Image / fw_payload.bin。
```

用户已授权本轮在服务器隔离目录直接调用原 CMake/bbkernel 流程，作为 MCP 工具缺失
时的限定例外；此授权不修改共享服务器工程。远程入口为
`scripts/remote_linux_gemmini.py --ssh-helper <私有配置路径>`，不保存或打印凭据，
构建总超时一小时。`software/build_gemmini_image.py` 复用固定版本依赖归档，
校验 15 个程序确实安装到 rootfs，再按已验证的 500 kHz CLINT 适配重新打包 OpenSBI。
远程入口默认 SDK/缓存为本次服务器位置，其他机器须覆盖 `--sdk`、`--cache-base`。
仓库外的私有配置模块提供 `connect(client)`，接收 Paramiko `SSHClient` 并连接服务器；
该函数从系统 SSH agent、环境或临时输入取得认证信息，不提交私有配置。
归档上传器使用同一公开接入接口的副本，构建和传输逻辑未改。
软件构建时间/工具链变化可能改变镜像摘要，
请使用该次构建产生的记录，不直接套用历史摘要。

实物入口 `host/check_linux_gemmini.py` 核验镜像与既有位流摘要，只写易失 FPGA SRAM，
用原 UART loader 写入并逐字节读回完整标准 payload 后才释放 CPU。Windows 使用
已安装的 FTDI D2XX UART B，临时延迟 2 ms，关闭恢复原值；不操作 EEPROM 或 JTAG A。
精简 BusyBox 未启用 `timeout`；运行器用已启用的 ash `sleep`、`kill`、`wait`
构造 90 秒 watchdog，并在程序结束后取消、回收它；主机再设独立 120 秒等待，
整个硬件会话限制一小时。每次运行独立保存原始日志、返回码和机器结果。

本机实际 Python 3.10.11、pyserial 3.5、paramiko 5.0.0、Vivado 2025.1；
FTDI D2XX DLL 产品版本 2.12.36.20。Windows 实物调用示例（从平台目录执行，
替换变量中的真实路径，关闭其他串口客户端）：

```powershell
$env:PYTHONUTF8 = '1'
python -m pip install -r host/requirements-gemmini.txt
$bit = 'D:\实际实现目录\toy_a7.bit'
$payload = 'D:\实际软件目录\fw_payload.bin'
$record = 'D:\实际软件目录\LINUX_GEMMINI_BUILD.json'
$sha = (Get-FileHash -LiteralPath $bit -Algorithm SHA256).Hash.ToLower()
python host/check_linux_gemmini.py --payload $payload --build-result $record --bitstream $bit --expected-bit-sha256 $sha --vivado 'D:\Xilinx\2025.1\Vivado\bin\vivado.bat' --port COM5
```

缺省摘要是本次已验证的 UART 位流 `ccc33c51…dffde1`。没有原二进制时，在安装了
Artix-7 器件支持的 Linux Vivado 2024.1 环境，按 [平台构建说明](../README.md#build)
运行 `scripts/elaborate.sh` 和 `scripts/start_board_build.py`（不加 `--flash`）。轮询
`RUN.json`，仅使用 `COMPLETED`、退出 0、`bitstream_generated=true`、实现检查通过的位流。
重建位流可能有不同摘要，需显式传入 `--expected-bit-sha256` 并保存其实现记录，
重新上板验证；该参数不赋予新产物历史验收结论。不能传入 Flash 目标位流。
关闭其他串口客户端，使用 PROG/UART USB；自动临时编程后，按顺序执行完整 DDR
读回、Linux 启动、原五项系统检查、新 16 项矩阵比较和原 13 项 Gemmini 测试。
日志在独立的 `build/hardware-gemmini-<日期>-<标识>/`。失败/超时记录与成功记录分开，
不能只凭 LED、进程返回 0 或构建成功认定全部功能通过。

如果完整 DDR 读回及 Linux 启动已完成、只需修正测试入口，可用
`--loaded-run <旧硬件运行目录>` 继续，避免重复传输。该模式核验旧加载记录，
再从实际 Linux 对 15 个已安装程序逐个执行 `sha256sum`；任何文件缺失或摘要不同
都会拒绝执行测试。断电或复位后须重新完整加载，不能沿用旧记录。

完成后，独立核对原始串口日志、15 个进程返回码、原测试成功标志和 16 个矩阵结果：

```bash
python scripts/verify_linux_gemmini.py --build-record <LINUX_GEMMINI_BUILD.json> --hardware-result <RESULT.json> --output <PERFORMANCE.json>
```

这里的 `RESULT.json` 必须来自硬件运行目录。`CPU/accelerator` 小于 1 表示本次
端到端加速器路径更慢；如实保留结果，不把小矩阵和软件搬运开销排除后宣称加速比。
核验重建位流的新结果时，同样传入 `--expected-bit-sha256 <检查过的摘要>`。

看门狗可单独复现，需要已经启动、空闲的 Linux shell；不重烧位流：

```powershell
python host/check_watchdog.py --port COM5
```

正常退出 0、非零退出 1、刻意让 `sleep 5` 触发 1 秒超时并返回 137，同时检查 watcher
已回收。记录保存在独立 `build/watchdog-<日期>-<标识>/`。归档的 `sources/` 是实际
执行版本；当前入口额外提供日期命名、新位流摘要参数和便携的 watchdog 入口，
这些包装改进不回写到历史实物记录。

准备/构建结果不代替实物通过证据。首轮只临时加载新软件镜像；
原 Flash 镜像作为恢复入口保留。确认 Linux/Gemmini 实物结果后，再更新固化镜像。
整模型验证尚未完成；LeNet 的固定版本源码核对见 [模型兼容性评估](MODEL_COMPATIBILITY.md)。
