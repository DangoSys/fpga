# 2026-10-13 补存原准备脚本

原档案未保存 `software/prepare_platform.py` 副本，核验器因此回退到当前源码。
当前版本新增测试脚本 overlay 后，不能继续把它作为旧实验输入。

现补存 `sources/software/prepare_platform.py`，字节来自 #10 的固定提交
`ccb40f13680689ccdd08a692f87e00fa5758f4dc`；已核验其 SHA256 与本档案原有
`build/INPUT_MANIFEST.json` 中对应条目完全一致。既有日志、输入记录、MANIFEST、
结果和原报告均不改。核验器优先使用已固定的旧副本，继续执行原摘要要求。

这是源码快照补存，不是一次新测试，也不改变旧镜像或验证资格。
