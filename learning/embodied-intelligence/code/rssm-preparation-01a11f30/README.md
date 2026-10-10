# 本次 RSSM 备课的教师核验代码

日期：2026-10-09。来源与贡献：AI 父 agent 自编，Python 标准库，代码版本 revision2；没有学习者贡献，没有神经网络训练或真实环境运行。

规范原件：verify_preparation.py。实际结果保存在 `../../artifacts/preparation-tests/2026-10-09-rssm-01a11f30/verification-output.json`，输出 revision2。

三项核验各有不同用途：

1. `sequence_elbo_check` 枚举两步二元潜变量模型的完整四条路径。因果 variational family 在第一步只使用第一步观测，第二步条件因子使用历史潜变量与当前观测；它不是把两个 exact filtering marginals 相乘。检查路径 ELBO 与重构减期望 KL 一致，gap 等于对完整序列 posterior 的 KL。每条概率来自本文件明定模型，不声称是论文实验。
2. `mean_substitution_check` 构造非线性函数 f(z)=z² 与对称两点分布，得到 E[f(z)]=1、f(E[z])=0。它反驳一般情况下将采样传播直接替成均值传播的等价性，不否定线性情形或有明确目的的近似。
3. `finite_bridge_check` 用 Fraction 精确传播两状态 belief，更新红／蓝观测，枚举 H=2 的四个候选。额外独立枚举物理状态路径，核对候选评分与 belief 递推一致。评价效用不作为观测反馈进入 filter；演示没有奖励数据记录。

图示原件：draw_dataflow.py revision1。输出 `11-online-dataflow.png` 只画 RSSM 在线使用的三种接口，不画训练过程。父 agent 实际查看输出，修复初稿字体缺字和箭头标签重叠后重新查看；最后图中文字可读，区分真实与候选状态来源。它是教学数据流图，不是观测到的实验结果。

运行：`python code/rssm-preparation-01a11f30/verify_preparation.py`（从学习目录启动）。无需安装新依赖。实际已运行且断言通过；只支持上述有限模型的程序行为与数值，不能替代一般 ELBO 证明、神经 RSSM 实现或闭环控制实测。

三个对象彼此分开：ELBO 枚举例不是材料中的动作规划桥；动作桥不是神经 RSSM；非线性反例不承担总体控制效果评价。理论连接与用途由备课原件说明。
