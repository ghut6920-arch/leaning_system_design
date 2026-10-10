# M4 视觉与表示

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 24；对应 G2。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M4.1 CNN 基础 | 通道、卷积核、stride/padding、输出尺寸、感受野、pool、卷积 encoder | 7 | A/B | 实现小 CNN，逐层标出尺寸 | M3 |
| M4.2 Representation 与 latent | 表征、embedding、encoder/decoder、bottleneck、AE 重建、冻结/微调 | 6 | A | 训练小 AE；说明“latent”不保证物理语义 | M4.1 |
| M4.3 ViT 与视觉 token | patchify、线性投影、位置、CLS/mean pooling、ResNet 直觉、预训练迁移 | 6 | A/B | patchify/unpatchify；M5 后完成 ViT block 接线 | M4.2；与 M5 联动 |
| M4.4 自监督与多模态 | contrastive learning、masked prediction、EMA/stop-gradient、CLIP/VLM 结构直觉 | 5 | B | 比较重建、对比、预测目标；画视觉语言接口 | M2–M4.3 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
