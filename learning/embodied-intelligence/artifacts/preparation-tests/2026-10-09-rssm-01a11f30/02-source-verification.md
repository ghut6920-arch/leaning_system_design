# RSSM 材料事实核验与来源台账

日期：2026-10-09。职责：材料研究与事实核验。版本：revision4（父 agent 统一符号、补初始化等价的参数条件与来源版本说明）；状态：prepared；仅交备课参考，未向学习者开展教学、未产生学习表现、未改学习进度。

本文件由本次实际委派的材料核验 agent 编写。只读取指定 AG2/SK02 规则和下列外部原始来源，没有读取其他学习记录、state、sessions 或已有备课。这里不替认知设计方设定目标，也不称已完成独立盲评。

## 1. 实际取得的规则与来源

实际读取的规则原件：

- `../../personal-learning-suite/src/agents/AG2-materials.md`，2026-10-05 修订。
- `../../personal-learning-suite/src/skills/learning-materials/SKILL.md`。
- 同 skill 的 `references/materials-workflow.md`、`references/domain-checks.md`。

使用 SK02 的读取、准备与核验部分；没有调用 synthetic runtime，没有导入 fixtures/examples 数据库。

来源读取日期均为 2026-10-09。PDF 页码从 1 开始；下列精读范围不是“全文已核验”。

| ID | 原始来源与版本 | 实际读清的范围 | 当前支持的用途与边界 |
|---|---|---|---|
| S1 | [PlaNet，PMLR 正式论文](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf)，Hafner et al., ICML 2019，PMLR 97:2555–2565；[出版页](https://proceedings.mlr.press/v97/hafner19a.html) | PDF 第 1 页 introduction 的模型误差限制；第 2–3 页 §2、Eq.(1)(2)、Algorithm 1；第 3–4 页 §3、Eq.(3)(4) 和 filtering/smoothing 说明；第 4–6 页 §4、Eq.(5)(6)(7)、停止梯度说明；第 8 页 discussion 的有限规划时域说明 | 核模型定义、动作时序、训练项、多步预测和 CEM/MPC 主线；不把实验结果推广成一般性能保证，不称全部图表、参考文献已审查 |
| S2 | [PlaNet 官方补充 PDF](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)，同一 PMLR 版本；文件包含正文和附录，共 20 页 | 第 12 页 Appendix A 的最终配置说明与 Appendix B Algorithm 2；第 14 页 Appendix D、Figure 8 图注；第 16 页 Appendix F，Eq.(8)(9)(10) 推导文本 | 核最终 RSSM 的 overshooting 选择、CEM 返回首动作、基础 ELBO 及 overshooting 理论限定；不声称重新证明 Eq.(10) 的 conjecture |
| S3 | [Dreamer 原论文](https://arxiv.org/pdf/1912.01603)，当前读取 PDF 标注 arXiv:1912.01603v3，2020-03-17，ICLR 2020 | 第 2 页 §2、Eq.(1)；第 3 页 Algorithm 1 与 imagination environment；第 6 页 §4 reconstruction、Eq.(9)(10) | 核 latent imagination 与在线观测的区别、共同 RSSM 训练项以及 Dreamer/PlaNet 行为生成区别；Dreamer 此版本的 p/q 字母约定与本单元相反，必须转换，不能直接复制 |
| S4 | [作者发布的 PlaNet 实现仓库 README](https://github.com/google-research/planet)，2026-10-09 读取 archived master 展示页 | README 的 Method、Instructions 中版本变化提示 | 补核执行首动作并在下一图像到来后重规划；没有读取或执行模型、优化器、环境包装代码，不能声称实现级通过 |

模态声明：本次读清的是 PDF/网页可提取文本与能无歧义重建的上述公式；Figure 2、3、8 只读取图注。网页截图调用没有提供可供查看的图像内容，故不计为图像读取，没有核曲线数值、图像箭头或视频。本文件以下公式是统一符号后独立展开的数学参考，不是逐字摘录原式。直接引文为零。

## 2. 统一符号、动作与奖励时序

采用以下教学约定：观察到时刻 t 的信息后选择 a_t；a_t 影响 t+1。记

\[
I_t=(o_{1:t},a_{0:t-1}),\quad
h_t=f_\theta(h_{t-1},z_{t-1},a_{t-1}),\quad
p_\theta(z_t\mid h_t),\quad
q_\phi(z_t\mid h_t,o_t).
\]

`z_t` 对应 PlaNet Eq.(4) 的随机状态 `s_t`；`h_t` 是确定性记忆；模型状态是二者的组合 `(h_t,z_t)`。本包统一将 `x_t` 留给物理隐态，避免把物理对象与学习表示混为同一对象。只写 `z_t` 不能一般地当作完整 Markov 状态，因为下一次转移还要使用 `h_t`。`p` 表示生成/转移分布，`q` 表示变分 encoder，`θ,φ` 可以共享部分参数；不同字母不意味着实现必须两套独立网络。[来源：S1，第 4 页 Eq.(4)](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=4)

`h_0,z_0` 在参考推导中固定；`a_0` 为约定的初始输入。实际序列若使用 learned initial prior、episode reset mask 或随机初态，要把相应初始项加回，不能把此推导当作所有实现的 reset 规格。

与主材料的初始化对应：此处固定的 `h_0,z_0,a_0` 先决定 `h_1=f_θ(h_0,z_0,a_0)`。在选定 θ 下，把这个值作为已给 `h_1`，以 `p(z_1|h_1)` 为初始 prior、从 t≥2 递归，便可从动作条件集合删去固定初始化输入 `a_0`，不改变此 θ 下的分布和 ELBO。若在训练时仍定义 `h_1=f_θ(h_0,z_0,a_0)`，必须保留它对 θ 的依赖与梯度路径；把它改成独立于 θ 的固定常数，会改变初始化规格，不能泛称整个参数优化问题等价。03—06 的主例选用直接给定 h1 的合法规格，动作输入记为 `a_{1:T-1}`；它与本段原记法在 h1 取同值的参数条件下对应。`a_0` 不是另一次学习者执行动作，也不产生 reset 奖励。随机或学出的初态需另核。

奖励 `r_t` 在本备课中表示**到达 t 时的奖励**，因此教学接口为 `step(a_t) → (o_{t+1},r_{t+1})`，对应奖励头 `p_θ(r_t|h_t,z_t)`。这是为保持公式、展开与规划估值一致而选的索引，不是声称原文所有数组都采用它：原文 Eq.(1)/(4) 按状态时刻写奖励，Algorithm 1 的环境 API 返回量却写 `r_t,o_{t+1}`。实际数据接入必须明确 reward 轴的移位；reset 没有 `r_1` 时，省略/mask 该项，不创造一条初始奖励记录。[核验原位置：S1，第 2 页 Eq.(1)、Algorithm 1](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=2)

Dreamer 原论文（2020，arXiv 修订版 v3）§2 Eq.(1) 的 representation 是 `p`，imagination transition 是 `q`。这里的 v3 是 arXiv:1912.01603 的文件修订号，不是后来的模型名称 DreamerV3。本单元保留 `q_posterior/p_prior`，引用 Dreamer 时按功能映射字母；RSSM 定义也不能和 Dreamer 的 actor/critic 学习算法合并成同一项。[S3，第 2 页 Eq.(1)](https://arxiv.org/pdf/1912.01603#page=2)

## 3. Joint、条件似然与过滤近似的准确连接

令 `A=a_{0:T-1}`、`O=o_{1:T}`、`Z=z_{1:T}`、`R=r_{1:T}`。以下是在固定动作输入下的生成模型，动作不是本似然要拟合的随机输出。假设给定 `(h_t,z_t)` 后 observation 和 reward 两个头条件独立，且 `h_t` 始终由同一条历史 latent 路径递推，则

\[
p_\theta(O,R,Z\mid A)
=\prod_{t=1}^{T}
p_\theta(z_t\mid h_t)
p_\theta(o_t\mid h_t,z_t)
p_\theta(r_t\mid h_t,z_t).
\tag{J}
\]

这里已代入确定性的 `h_t`，不是漏掉随机变量：若把 `h_{1:T}` 序列显式加入 joint，应增加对应递推的 Dirac 约束（不与规划动作数 H 重载同一个符号）。没有观测到的 reward 项先积分掉，等价于删去其 log-likelihood 项。条件似然是

\[
p_\theta(O,R\mid A)=\int p_\theta(O,R,Z\mid A)\,dZ,
\]

它与有 latent 的 joint、与 `p(A,O,R)`、与最终控制回报分别是不同对象。动作由行为策略生成这一现实，不需要加入本次固定动作条件模型的 ELBO；也不能仅由条件似然宣称已识别真实环境的所有反事实因果效应。以上是对 S1 Eq.(2)(4) 和 S2 Eq.(8) 的统一符号展开。[S1，第 3–4 页](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=3)，[S2，第 16 页](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=16)

使用因果 encoder family：

\[
q_\phi(Z\mid O,A)
=\prod_{t=1}^{T}q_\phi(z_t\mid h_t(z_{<t},A),o_t).
\tag{Q}
\]

虽然左边写完整序列，右边第 t 个条件分布没有输入 `o_{t+1:T}`。这些因子不是各时刻独立的 `q(z_t)`：采样过往 `z` 改变了当前 `h_t`。对 sampled history 做递推得到过滤近似，其 marginal 可简写为 `q_filter(h_t,z_t|I_t)`；不能声称它恰好等于真实环境 filtering posterior，甚至也未必恰好等于生成模型的 exact filtering posterior。

Full smoothing 使用整个 observation 序列来估计更早状态，例如 `p_θ(z_t|O,R,A)`；它与只用到当前信息的 filtering 信息集不同。原文明确选择 filtering，亦说明训练可选择 smoothing。本参考后续采用 (Q)，因此不能悄悄加入双向 encoder 后仍称同一在线接口。离线训练 smoothing 是合法的不同变分选择；在在线滚动预测时读取真实未来观察则是信息泄漏。[S1，第 4 页 Variational encoder 续段](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=4)

## 4. 基础 sequence ELBO：经路径分解核验的教师参考

在支持与可积条件成立时，由 Jensen 不等式有

\[
\begin{aligned}
\log p_\theta(O,R\mid A)
&=\log\mathbb E_{q_\phi(Z\mid O,A)}
\left[\frac{p_\theta(O,R,Z\mid A)}{q_\phi(Z\mid O,A)}\right]\\
&\geq\mathbb E_{q_\phi}
\left[\log p_\theta(O,R,Z\mid A)-\log q_\phi(Z\mid O,A)\right]
\equiv\mathcal L_{\rm base}.
\end{aligned}
\]

代入 (J)(Q)，再对 `z_t` 作条件期望：

\[
\boxed{
\mathcal L_{\rm base}
=\sum_{t=1}^T
\mathbb E_{q_\phi(z_{<t}\mid O,A)}
\left[
\mathbb E_{q_\phi(z_t\mid h_t,o_t)}
\left[\log p_\theta(o_t\mid h_t,z_t)
+\log p_\theta(r_t\mid h_t,z_t)\right]
-\mathrm{KL}\!\left(q_\phi(z_t\mid h_t,o_t)\,
\Vert\,p_\theta(z_t\mid h_t)\right)
\right].
}
\tag{E}
\]

初始 history 是空集；缺失 reward 项依 §2 省略。这一分解保持重构/奖励项的正号、KL 的负号、`q || p` 的方向以及随机 history 的外层期望。省略外层期望时必须说明正在展示单条 reparameterized 采样估计，不把随机 `h_t` 当作全局固定常数。最小化训练 loss 时使用 `-L_base`。对单位方差 Gaussian observation/reward 头，负 log-likelihood 与平方误差只在含系数与加法常数的意义上对应，不能把此对应推广到任何 decoder 分布。

核验方式：独立把 joint 与 q 的 log 逐项展开；用 conditional expectation 将每一时刻的 `E_q[log p(z_t|h_t)-log q(z_t|h_t,o_t)]` 改写为负条件 KL；再与 PlaNet Eq.(3)(4)、Appendix F Eq.(8) 和 Dreamer 原论文的 arXiv 修订版 v3 Eq.(9)(10) 的结构对照。以上公式不是把原文 shorthand 中的 `q(z_t|o_{≤t},a_{<t})` 机械当成与 latent history 无关的独立 marginal。[S1，第 4 页](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=4)，[S2，第 16 页 Eq.(8)](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=16)，[S3，第 6 页 Eq.(9)(10)](https://arxiv.org/pdf/1912.01603#page=6)

另一个可直接审查的恒等式为

\[
\log p_\theta(O,R\mid A)-\mathcal L_{\rm base}
=\mathrm{KL}\!\left(q_\phi(Z\mid O,A)\,
\Vert\,p_\theta(Z\mid O,R,A)\right).
\]

这是本次独立推导：基础 ELBO 的 gap 对照的是**完整序列的 exact posterior**，即使所选 `q` 是 causal filtering family，也不能把 gap 右侧随意改成某个逐时刻 filtering posterior。Reward 不是 `q` 的输入不妨碍下界成立；只是限制了 variational family。

`β` 加权、free nats clipping、额外 global prior、overshooting 都要与未改写的数学 (E) 分开。部分改写仍可能满足某种下界条件，但不能不说明条件就称“正好是原 sequence ELBO”。PlaNet 最终实现的 free nats 配置已见 S2 Appendix A；本次没有执行任何训练，也没有核其实现代码。

## 5. 多步 prior 展开与未来观察边界

在真实时刻 t，先按 (Q) 从已知 `I_t` 建立当前状态近似。对候选动作 `a_t,…,a_{t+H-1}`，逐步使用

\[
\widetilde h_{t+k}=f_\theta(\widetilde h_{t+k-1},
\widetilde z_{t+k-1},a_{t+k-1}),\qquad
\widetilde z_{t+k}\sim p_\theta(z_{t+k}\mid\widetilde h_{t+k}),
\quad 1\leq k\leq H.
\tag{P}
\]

`(\widetilde h_t,\widetilde z_t)` 从当前过滤近似取样。第一个未来状态已用 prior，不能用真实 `o_{t+1}` 的 `q` 去“帮助一步”；以后也不输入真实未来图像。多个 transition 核组合并积分中间状态定义多步预测分布；单次 path rollout 是它的 Monte Carlo 样本，不等于完整预测分布。对 RSSM，应在 `(h,z)` 的完整状态上理解组合，不能把一般 `z` 单独写成 Markov 转移链。[S1，第 5 页 Eq.(5)](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=5)，[S3，第 2–3 页 latent imagination](https://arxiv.org/pdf/1912.01603#page=2)

训练 unroll 每步用真实 `o_t` 推断 posterior，和从 t 起看不到真实未来观察的 prior rollout 是两种信息条件。前者重构好，不构成后者多步预测已好。训练时未来 loss 对较早参数反传梯度，是优化整段序列，并不等于 encoder 前向读取了真实未来图像；泄漏应查具体输入与测试切点。

## 6. Latent overshooting 的限定用途

overshooting 增加从更早 posterior 出发、沿多个 prior transition 展开的训练压力，并使预测分布接近相应 informed posterior。它是 (E) 之外的可选多步目标/正则设计；不是 RSSM 结构定义，也不是运行 (P) 的必要条件，更不是本单元必须实现的步骤。原论文最终 RSSM agent 不要求它；附录 D 图注报告 RSSM 加该项在其实验中略降表现。[S1，第 5 页 §4](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=5)，[S2，第 12 页 A、第 14 页 D](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=12)

教师核验必须保持以下边界：

- 真正展开时，中间状态来自 prior；目标 posterior 可以在训练时使用目标时刻真实观察，不能反过来让未来观察进入被评估的 prior 路径。
- 对应 posterior path 的 `h_t^post` 与多步 prior path 的 `\widetilde h_t` 通常不同；不能写一个 `h_t` 后暗换来源。
- 原文 Eq.(6)(7) 经 Appendix F Eq.(9) 的另一次 Jensen 展开含对中间 prior 路径的期望。这不允许直接声称“sampled conditional Gaussian 的 KL”恰好等于“对完整多步 marginal mixture 的 KL”。要保留外层期望/采样近似的区分。
- 原文实践对距离 `d>1` 的 posterior target 停止梯度；这是具体训练方向，不是每种可能的多步损失定义。
- Eq.(6) 对原一步模型 likelihood 也构成下界的论述，正文和附录明写 **conjecture**，还有限定为数据分布期望的表述；不可升级为本单元已经证明的普遍定理。任意权重、截断或额外实现损失也不可自动获得同一 ELBO 解释。

这些是目标结构核验；未实施、未运行或证明 overshooting 通用实现。[S1，第 5–6 页 Eq.(6)(7)](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=5)，[S2，第 16 页 Eq.(9)(10)](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=16)

## 7. CEM、MPC 与闭环接口

本备课定义 H 为动作/transition 数，动作序列为 `a_{t:t+H-1}`，未来奖励为 `r_{t+1:t+H}`。原 Algorithm 2 使用 inclusive `a_{t:t+H}` 并将 H 称 horizon distance；引用时要明确这一索引差，不能把两个 H 的含义混用。[S2，第 12 页 Algorithm 2](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=12)

一次 CEM 搜索的变量是候选动作序列的分布参数，和 RSSM 中 `q_φ` 的 latent inference 不同。可执行核验顺序为：

1. 从当前 `q_filter(h_t,z_t|I_t)` 出发；建立动作序列的 Gaussian proposal。
2. 采样 J 个候选，各自按 (P) 展开；用 reward head 的预测均值之和估值。
3. 按估值取 top K，重拟合 proposal 的均值/离散度，重复 I 次。
4. 取最终 proposal **首动作的均值**执行，不执行整段计划。
5. 获得真实 `(o_{t+1},r_{t+1})`；用实际执行 `a_t` 更新 `h_{t+1}`，以新 `o_{t+1}` 做 posterior correction，再从新状态重新规划。

PlaNet 原论文每个候选评估一条 sampled latent trajectory，沿该条轨迹求 reward mean 的和。写多条轨迹的平均作为一般 Monte Carlo 扩展是合理的教学改写，必须标为扩展，不能称原 PlaNet 已使用多粒子期望估计。论文最终返回的是首动作均值，不保证它恰好等于某个已采样 candidate 的首动作。CEM 给的是近似搜索结果，不保证全局最优。实际 action repeat 的 R 个环境原始步构成一个模型决策步；“执行首动作后重观测”应按该决策步解释。[S1，第 3 页 Planning algorithm](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=3)，[S2，第 12 页 Algorithm 2](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=12)

规划时 observation decoder 不必生成图像；奖励头直接读取 latent state 即可评分。MPC 的关键闭环是**新真实观察 → posterior correction → 新规划**。一次从 t 起只按 prior 展开完整动作段属于 open-loop prediction；环境一直执行旧动作段而没有观测后重规划，不能叫本参考的 receding-horizon MPC。[S4 Method](https://github.com/google-research/planet#method)

Dreamer 共用 latent dynamics 的思想，但行为通过 imagination 学出的 actor/value 来生成；不应把其 Algorithm 1 描述为每步 CEM 搜索。[S3，第 3 页 Algorithm 1](https://arxiv.org/pdf/1912.01603#page=3)

## 8. 可用于教师反馈的事实边界

以下结论是对已核模型与接口的推论，不是新的实验结果：

- `ELBO/reconstruction 改善`、`held-out prior 多步预测改善`、`闭环回报改善` 是三个不同证据对象。第一项不会自动证明后两项；要分别检查未来观察可见性、action 分布和真实闭环结果。
- 有限容量/受限分布 family 下，一步最优通常不等于多步最优；规划搜索还可能选择训练数据覆盖不足的动作。[原论文问题限定：S1，第 1 页与第 5 页 Limited capacity](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=1)
- 一个独立数学反例锚点：若已收集数据的动作全为 0，则 `x_{t+1}=x_t+a_t` 和 `x_{t+1}=x_t+10a_t` 对该数据给出相同 transition。它们对候选 `a_t=1` 的预测不同。训练数据上的相同似然不足以裁定这一未覆盖动作的规划表现。此反例是人工构造，不是环境实验或学习者记录。
- `p_θ(z_t|h_t)` 有随机方差，可以表达模型所学的条件随机性；它不是参数 posterior `p(θ|D)`。仅有一个随机 RSSM 不自动给出对模型失配、分布外动作和未知参数的校准置信度。重规划提供纠正机会，也不会保证抵消模型偏差或有限时域/search 误差。[原论文 caveats：S1 introduction](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=1)

明确未核：真实学习者能力/前置与既往暴露、任何本地 learning code、训练运行、测试数据、多模态成图、闭环实验、最新 RSSM/Dreamer 变体或额外 uncertainty 算法。不在本次范围内宣称 loss、rollout 或控制检查“通过”。

交接：本台账可供主备课入口检查其公式、推导、图箭头、题面与教师参考的事实一致性。认知目标、教学策略、实际展示与学习证据判断由相应职责另行处理。
