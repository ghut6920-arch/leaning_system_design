# M0 工程与张量

依据：[原大纲](../../course/original-syllabus.md)第 5、6、7 节。课程建议学时 18；对应 G0。当前没有学习表现，不预设起点。只在产生相关活动时按目标细化；本文件不是完成记录。

| 模块与章节 | 子章节和范围 | 学时 | 等级 | 学习成果 | 依赖 |
|---|---|---:|---|---|---|
| M0.1 Python 最小基础 | 变量、循环、函数、容器、类、import、异常、路径和文件读写 | 3 | A | 将 notebook 中一个数据处理函数移入脚本 | 无；零基础另补练习 |
| M0.2 张量操作 | NumPy/PyTorch、shape、索引、broadcast、reshape、permute、矩阵乘、einsum | 5 | A | 图像/视频/序列三种张量变换练习 | M0.1 |
| M0.3 PyTorch 工作流 | nn.Module、Parameter、Dataset/DataLoader、forward、autograd、optimizer | 4 | A | 跑通简易回归训练循环并解释每步 | M0.2；与 M2 联动 |
| M0.4 环境和命令行 | 虚拟环境、Conda 或 venv、依赖记录、Linux 路径、进程、日志；tmux 够用 | 3 | B | 从终端启动和恢复脚本；确认 VSCode interpreter | M0.1 |
| M0.5 实验记录 | Git 基本使用、config、随机种子、checkpoint、数据与版本记录 | 3 | B | 给出可复现说明和一个保存/载入案例 | M0.3–4 |

阶段要求见 [目标候选](../../goals/course-goals-draft.md)。问题在 [questions](../../questions/README.md)，真实会话在 [sessions](../../sessions/README.md)，连续产物在 [artifacts](../../artifacts/README.md)，下一步以 [当前状态](../../state/current.md)为准。
