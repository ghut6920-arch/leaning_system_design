# M3 神经网络与训练

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 38；对应 G1。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M3.1 MLP 与非线性 | Linear、ReLU、GELU、SiLU、sigmoid/tanh、表达能力、logits | 8 | A | 实现两层 MLP，解释无非线性时的退化 | M1–M2 |
| M3.2 反向传播 | 计算图、链式法则、向量化梯度、梯度累积、detach、requires_grad | 10 | A | 手推小网络，和 autograd/数值梯度交叉验证 | M3.1 |
| M3.3 训练优化 | mini-batch SGD、momentum、Adam/AdamW、学习率、warmup、weight decay、初始化、梯度裁剪 | 10 | A/B | 排查学习率与梯度问题；生成诊断记录 | M3.2 |
| M3.4 深层网络组件 | residual、Dropout、BatchNorm/LayerNorm 区别、train/eval、梯度消失/爆炸 | 6 | A/B | 比较残差/非残差，解释归一化轴 | M3.2–3 |
| M3.5 训练工程补充 | device/dtype、no_grad、混合精度概念、吞吐/显存、保存恢复 | 4 | B | 记录参数量、峰值显存或内存与配置 | M0.5、M3.3 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
