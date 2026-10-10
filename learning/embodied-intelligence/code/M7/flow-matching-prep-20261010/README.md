# M7.2 教师 CFM 运行与采样器规格 / revision 1

日期：2026-10-10。此项目属于备课审查，全部初版代码由实际教师代码 Agent（AI）编写；没有学习者提交或运行，也不构成真实学习进度。上游内容来自备课目录 `00-disciplinary-analysis.md` r1 与 `01-cognitive-design.md` r1。训练、解析参照、实验及图使用同一 Gaussian 设定。

| 原件 | 用途 |
|---|---|
| `teacher_cfm.py` | 完整教师实现：抽样、68 特征真实 OLS 拟合、oracle 对照、Euler、同噪声评估与结果保存 |
| `learner_sampler.py` | 同签名核心空白，尚无学习者实现 |
| `SAMPLER_SPEC.md` | 不依赖教师完整循环代码的采样器行为规格 |
| `mathematical_checks.py` | 关键导数／参数有限差分／精确解／步数与 shape／解析边界核验 |
| `make_figures.py` | 从保存的真实运行结果生成两张教学科学图及 SVG |
| `provenance-r1.json` | 来源、贡献、各代码原件 SHA-256；由本次实际生产结束后保存 |

当前教师环境是 `E:/anaconda/python.exe`，已有 NumPy/Matplotlib；不依赖 PyTorch，不安装包。由本学习目录执行：

```powershell
& 'E:/anaconda/python.exe' 'code/M7/flow-matching-prep-20261010/mathematical_checks.py'
& 'E:/anaconda/python.exe' 'code/M7/flow-matching-prep-20261010/teacher_cfm.py'
& 'E:/anaconda/python.exe' 'code/M7/flow-matching-prep-20261010/make_figures.py'
```

默认输出在 `artifacts/preparation-tests/2026-10-10-M7-2-flow-matching/teacher-run/` 与 `figures/`，只作 AI 教师运行审查。复现应指定新的 `--out-dir` 以保留本次 r1 结果；随后作图 `--run-dir` 指向该复现输出，`--figure-dir` 指定新图目录。训练 seed 可重建数据，没有保存整份训练集；权重、held-out 输入和同噪声生成对照已保存。

训练实际抽取独立 X₀、X₁，监督为 U=X₁−X₀。类标半数 0、半数 1 后随机打乱；t 连续均匀抽样。17 个 hat 时间节点乘 `[1,x_coord0,x_coord1,2c−1]`，其中两个 x 项是当前状态坐标；不使用 μ 中心化输入或 oracle 标签。OLS 直接求有限经验 coordinate-MSE 最小点，不声称运行梯度训练。局部 b 更新另有手算/数值对照，不能与完整 W 的优化过程混称。

固定 t,c 时模型对 x 仿射。因此能拟合 Gaussian 主例的场结构并近似时间变化，不能充分表示同 c 双峰的非线性后验权重；双峰函数只提供解析辅助。oracle 解析速度与 exact 轨迹只用于核验、误差和教学对照。

`euler_sample(field,z,c,n_steps)` 的输入只有当前位置可查询的场、初始噪声、可用类标、正整数 N，输出 t=1 状态。N 次场查询是成本代理；实际墙钟时间另外记录，并不承诺硬件间可比。增加 N 固定同一 W。高步 learned reference 是有限 Euler 参照，以加倍 N 变化检查稳定性，不能称 exact。图中坐标都是玩具状态单位，t 是生成时间。

用户若在审查中读取了完整实现，后续当前代码工作只能如实称支持下实现／修改／追踪，不能补称未知实现的独立测试。学习者原版和修订要保留不同文件名或版本，不能覆盖本教师 r1 原件来伪装自己的实现。

项目没有神经网络训练、同 c 双峰训练、超参搜索、跨 seed 比较、真实动作模型或机器人执行。数字结果与有限结论见备课目录 `07-code-and-run-review.md`。
