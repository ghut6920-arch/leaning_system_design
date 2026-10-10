# M6 生成与潜变量

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 22；对应 G4。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M6.1 生成建模地图 | p(x)、p(x\|c)、likelihood、采样、多峰；区分架构/目标/采样器 | 4 | A | 用同一任务比较均值回归与分布生成 | M1、M2 |
| M6.2 信息论 | entropy、cross-entropy、KL、NLL、支持集、方向与非对称 | 6 | A | 推导 H(p,q)=H(p)+KL(p\|\|q)，解释条件限制 | M1.3、M2.2 |
| M6.3 潜变量模型 | prior/posterior、AE/VAE、reparameterization、ELBO 关键两步、重建/正则 | 8 | A/B | 标出 q 与 p 的方向；实现重参数化和 Gaussian KL | M4.2、M6.2 |
| M6.4 生成序列与条件 | 自回归分解、encoder latent 与预测 latent 区分、训练与采样、条件失效 | 4 | A/B | 比较视频与动作建模的条件变量 | M5、M6.1–3 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
