# Toy 8×8 的模型兼容性评估

本评估区分“模型能够分块计算”和“已有 ModelTest 二进制兼容”。硬件来源固定为
Buckyball `1f3d54535bd5fb76d5fd2f6b05ed36e591cf3097`；其 ModelTest 子模块固定为
Buddy Examples `74a062b8e607e0806c2423f639daad650b8d82be`，不混用最新主分支结果。

## 已核对的构建路径

- 该版本 `models/archs/buckyball/` 有 goban、pebble、poly 布局，没有 toy。
  架构选择 CMake 在缺少对应目录时明确报错，因此不能直接声称 `--chip toy --model lenet`
  是现成可用的模型组合。
- LeNet 的 Buckyball 路径位于 `models/archs/buckyball/pebble/LeNet/`，通过
  Tile/Buckyball lowering 和物理 bank 分配生成代码，目标是 Pebble。
- 独立的 `models/archs/gemmini/LeNet/` 使用 `convert-linalg-to-gemmini`、
  `lower-gemmini` 和 `+xgemmini`。该名称不保证生成的指令编码、DMA 和片上存储布局
  兼容本项目的 GemminiBall；需要核对实际 LLVM/反汇编，不能直接替换目标名。
- 模型数据通过标准模型导入生成：`params.f32`、`weights.i8`、`scales.bin` 和 MLIR。
  模型执行文件依赖这些资源，打包一个 ELF 不等于拥有完整模型镜像。

## 当前 FPGA 的约束

实际 profile 只保留 GemminiBall 的 23 个算子编码，以及基础访存/同步指令。
原 Toy 的独立 MXFP2INT、RELU 和 BDB_COUNTER 已移除，没有自动软件回退。
软件必须使用实际 8×8、64-bit bank、8 physical/16 virtual banks 参数。
不能把所有 `16` 常量直接替换为 `8`；矩阵维度、bank 宽度及指令字段是不同概念。

8×8 只限制每次子块的并行规模，较大矩阵可以分块。保持数据类型、累加、缩放和
舍入语义后，模型结构不需要因阵列缩小而改变。同频 PE 数从 256 降到 64，
理论峰值减少为四分之一；整模型耗时还受分块、CPU 算子及数据搬运影响。

## LeNet 的后续验收

先完成 Linux/Gemmini 实物算子验证，再补齐 Toy 模型构建目标及匹配的 lowering。
应使用同一份固定训练权重、量化参数和输入，对照 CPU 参考的逐层输出和最终分类。
ReLU、池化、量化等若改由 CPU 实现，必须明确记录，不能宣称它们由已移除 Ball 执行。
同时核对资源打包、运行内存和最终执行的自定义指令。

目前没有 Toy 8×8 整模型通过证据。本文件记录的是源码核对结果，不是模型性能报告。

## 固定版本来源

- [ModelTest 架构选择](https://github.com/buddy-compiler/buddy-examples/blob/74a062b8e607e0806c2423f639daad650b8d82be/models/archs/buckyball/CMakeLists.txt)
- [Pebble LeNet 构建](https://github.com/buddy-compiler/buddy-examples/blob/74a062b8e607e0806c2423f639daad650b8d82be/models/archs/buckyball/pebble/LeNet/CMakeLists.txt)
- [独立 Gemmini LeNet 构建](https://github.com/buddy-compiler/buddy-examples/blob/74a062b8e607e0806c2423f639daad650b8d82be/models/archs/gemmini/LeNet/CMakeLists.txt)
- [LeNet 模型与数据生成](https://github.com/buddy-compiler/buddy-examples/blob/74a062b8e607e0806c2423f639daad650b8d82be/models/models/LeNet/CMakeLists.txt)
