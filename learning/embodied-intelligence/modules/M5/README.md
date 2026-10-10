# M5 Transformer 核心

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 60；对应 G3。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M5.1 Token 与序列 | 离散/连续 token、embedding、batch/sequence/feature、基本 tokenization | 5 | A/B | 给文字、图像、动作分别定义 token 和 shape | M0、M4 |
| M5.2 Attention 与 QKV | 线性投影、scaled dot product、softmax、attention map、缩放与复杂度 | 10 | A | 从头实现单头 Attention，手算与程序对照 | M1–M3 |
| M5.3 多头与完整 block | split/merge heads、output projection、residual、LayerNorm、MLP、Pre-LN/Post-LN；RMSNorm/SwiGLU 够用 | 8 | A/B | 实现 pre-norm block，逐层标形状 | M5.2、M3.4 |
| M5.4 位置与 mask | learned/sinusoidal position、RoPE、padding/causal/block-causal、label shift、泄漏检查 | 8 | A | 写 RoPE 和 mask；扰动未来 token 验证不可见性 | M5.3、M1.1 |
| M5.5 架构与训练推理 | encoder、decoder、encoder-decoder、decoder-only、teacher forcing、autoregressive rollout、KV cache 原理 | 9 | A/B | 训练小 decoder-only 模型；对照三种结构 | M5.4、M2.2 |
| M5.6 Cross-Attention 与条件 | Q/KV 来源、不同 token 数、投影、拼接条件、cross-attn、FiLM/adaLN、条件 drop | 8 | A/B | 用动作 query 读取视觉/语言条件；构建条件 block | M5.2–5 |
| M5.7 视觉与时空 token | ViT 接线、视频 tubelet、时间/空间位置、全局/分解时空注意力、视频—动作对齐 | 7 | A/B | 对视频和 action chunk 画含时间轴的 token 图 | M4.3、M5.6 |
| M5.8 成本与综合验收 | 参数/激活/KV cache、N² 注意力成本、长序列、官方 SDPA 对照、一个消融 | 5 | A/B | 通过数值、信息流、学习曲线与消融验收 | M5.1–7 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
