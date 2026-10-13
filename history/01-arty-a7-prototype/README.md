# 阶段 01：最早 A7 原型

这是旧 `platforms/arty-a7/` 工程，首次提交为 `1e6e406`，完整源码和原验证记录在
[project/](project/README.md)。它是早期功能子集，已不作为当前使用入口。

- 目标 Arty A7-100T；RV64IMAC、4 KiB 缓存，50 MHz。
- 128 KiB BRAM 程序/数据存储，115200 UART；SMatMul 8×16、MatAdd、ReLU。
- 没有 Linux、虚拟内存或 FPU，也没有后续 Toy 的 DDR 系统。
- 具体仿真、综合和上板边界以 [原验证说明](project/VALIDATION.md) 为准。

此阶段解决了独立 A7 硬件适配，但未满足完整软件系统要求，因此进入
[阶段 02](../02-toy-linux/README.md)。当前项目见 [Toy/Linux](../../platforms/arty-a7-toy/README.md)。
归档中的命令是原布局；若要重建，使用 `git checkout 1e6e406` 的独立工作树。
