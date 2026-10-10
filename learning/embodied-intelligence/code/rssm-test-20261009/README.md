# 备课教师数值核验 v1

作者：本聊天主 AI agent；日期：2026-10-09。来源：自拟的一维 Gaussian RSSM 教学规格及标准 Gaussian 条件/矩公式，不是论文参数、学习者实现或真实机器人代码。

`verify_toy.py` 使用 Python 标准库。实际运行环境 Python 3.12.3，无依赖安装。执行入口：

```text
python code/rssm-test-20261009/verify_toy.py
```

完整 stdout 保存在 `../../prep/rssm-test-20261009/09-numerical-check.json`；包括范例及 W1/W3 新数据的轨迹、完整 q 的解析 ELBO、由 Kalman 更新计算的模型 log evidence、九个候选和重规划表。它核算期望、索引与候选排序；不训练网络、不复现论文、不测学习者表现。

`workflow-specs.txt` 是材料 agent 设计、主 agent 规范保存的三个非执行伪代码原件（v2）；题面04引用其内容。v2根据审查显式绑定流程A的state/root/已执行动作/新观测，题面同步，其他用途不变。它用来检查信息集与用途，并未作为控制器运行。

三个运算范围必须分开：

- `representative_trace` 用代表性均值路径解释依赖顺序；本线性模型下均值恰与完整 q 的均值一致，协方差仍不能丢。
- `exact_variational_elbo` 对过滤联合 q 的全部历史不确定性取解析期望；`exact_log_evidence` 用生成模型 Kalman 过滤独立计算 evidence，二者的差非负。
- `rollout` 固定给定 h，保留条件 root 的 z 随机性和未来 prior 噪声；new-o 到来后再用均值锚点固定下一 h。这是明确的条件 root 控制支架，不能称完整 latent-belief MPC。

各候选的方差项在此线性同方差模型中相同。因此保留方差可得到正确绝对期望成本，本例的候选排序不因这个共同项改变；不能由本例声称风险处理改变了动作。完整联合 root 的一般规划接口由正文另给。

所有高斯的第二参数为方差；最小化二次 cost 等价最大化其负 reward。枚举有限九候选不等于运行 CEM，不证明连续域最优性。代码版本以本次交付包 manifest 的 SHA-256 定位；后续改动须更新该定位及实际结果。
