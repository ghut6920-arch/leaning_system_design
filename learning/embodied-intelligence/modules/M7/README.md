# M7 扩散、流匹配与 DiT

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 26；对应 G4。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M7.1 Diffusion 桥接 | Gaussian 加噪、noise level、噪声预测、去噪采样、DDPM 训练/采样框图、score 含义 | 10 | A/B | 2D 或低维序列去噪模型；说明训练为何无需展开全部步 | M3、M6 |
| M7.2 Flow Matching 桥接 | 噪声到数据路径、条件向量场、期望回归、ODE/Euler、时间方向 | 10 | A/B | 2D conditional FM；改变步数比较采样误差/成本 | M1.2–3、M3、M6 |
| M7.3 DiT 与视频桥接 | patch/latent、时间 embedding、adaLN、预测头、视频轴；看网络与损失如何独立组合 | 6 | A/B | 阅读 DiT block；构建极小条件 Transformer 生成头 | M4、M5、M7.1–2 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
