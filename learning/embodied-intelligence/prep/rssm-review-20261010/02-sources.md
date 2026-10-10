# RSSM 技术契约与原始来源核验

状态：2026-10-10 备课候选；仅供本次审查。未开展教学，未读取其他学习记录，未更新学习进度。职责：本文件只给材料制作与审查提供技术边界，不代替认知设计。

## 1. 来源身份、已读范围及定位

| 来源 | 本次实际打开和读取 | 可支持的用途 | 未覆盖 |
|---|---|---|---|
| Hafner et al., *Learning Latent Dynamics for Planning from Pixels*, ICML 2019, PMLR 97:2555–2565 | [出版页](https://proceedings.mlr.press/v97/hafner19a.html)；[主文 PDF](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf) §2 PDF pp.2–3，§3 pp.3–4 式(2)–(4)、Figure 2，§4 pp.4–6 式(5)–(7)、Figure 3；实际读取文本抽取 | 历史 PlaNet/RSSM 定义、filtering、ELBO、rollout/overshooting/MPC/CEM 的区分 | 未复现论文实验；没有把全文打开称为全文精读 |
| 同论文 [含附录版本](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf) | Appendix A PDF p.12；B p.12 Algorithm 2；D p.14 Figure 8 及结论；F p.16 式(8)–(10)；实际读取文本抽取 | 实际规划次序、标准变分推导、overshooting 的额外 Jensen 步骤、实验适用边界 | PDF 截图工具报不可用，未声称完成像素级图/公式排版核对；关键公式另用独立推导和作者代码交叉核验 |
| [作者发布的 RSSM 代码](https://github.com/google-research/planet/blob/master/planet/models/rssm.py) | `master`，2026-10-10 实际读取 `_transition`、`_posterior`、`dist_from_state`、`features_from_state`；[raw](https://raw.githubusercontent.com/google-research/planet/master/planet/models/rssm.py) | 核同时间 prior/posterior 共用 deterministic belief；KL 作用于 stochastic Gaussian；decoder 接收 sample 与 belief | 未下载、未运行、未核完整训练程序；`master` 是检索时版本，不声称为冻结实验 commit |
| [作者发布的 CEM 代码](https://github.com/google-research/planet/blob/master/planet/control/planning.py) | `cross_entropy_method`；[raw](https://raw.githubusercontent.com/google-research/planet/master/planet/control/planning.py) 行21–59 | 核动作采样/裁剪、无观测 latent rollout、elite 重拟合均值与方差 | 不用 PDF 文本抽取中可能失真的标准差表达式做数值题依据 |
| Hafner et al., *Dream to Control: Learning Behaviors by Latent Imagination*, ICLR 2020 / arXiv:1912.01603v3 | [原文 PDF](https://arxiv.org/pdf/1912.01603) pp.1–2 §1–2；p.6 §4 式(9)–(10) 与 reconstruction 段；实际读取文本抽取 | 仅用于对照 PlaNet 的在线动作搜索与 Dreamer 的想象中 actor/value 学习；Dreamer 原文的 p/q 命名与本单元不同 | 不引入 DreamerV2/V3 的离散 latent、KL balancing 等技巧；不以现代配方替代原始 ELBO |

页数均为 PDF 一基页码，非工具零基页码。论文内页码与主文 PDF 页码一致，含附录版本继续到 p.20。下文公式是独立重写，不是逐字翻译或原文截图。

## 2. 本次统一符号与时序

先在材料入口明确这条规范，所有图、公式、toy、伪代码与题面都遵守：

\[
a_{t-1}\longrightarrow x_t\longrightarrow(o_t,r_t)\longrightarrow a_t.
\]

`x_t` 是环境隐藏状态；真实 belief 记 `β_t^env=P(x_t|H_t)`；模型状态是 `s_t^m=(h_t,z_t)`，一般不能与 `x_t` 等同，模型过滤分布也不默认等于真实 belief。`o_t` 是当前观测，`r_t` 是到达状态 t 时记录的奖励，`a_t` 在读取 `o_t` 后选择并作用于 t→t+1。实际 API 若在 `step(a_t)` 后返回 reward，本材料把它记作 `r_{t+1}`；数据列必须显式重排，不能靠默认下标猜测。若任务的奖励直接依赖当前动作，改用相应 reward head 并重写因子化，不能沿用此处 `p(r_t|h_t,z_t)` 偷换条件。

PlaNet 原文随机模型状态记作 `s_t`；本单元改作 `z_t`，以免与环境状态及整个模型状态混淆。`h_t` 是确定性递推量，`z_t` 是随机量。确定性指“给定上一步模型状态与动作后由函数确定”，并不指它跨所有随机轨迹都取同一值，也不等于真实物理状态。

固定 `h_0,z_0`，给定 `a_{0:T-1}`；`a_0` 可为约定的初始空动作。定义

\[
h_t=f_\theta(h_{t-1},z_{t-1},a_{t-1}),\quad
p_\theta(z_t|h_t),\quad
q_\phi(z_t|h_t,o_t),\quad
p_\theta(o_t|h_t,z_t),\quad
p_\theta(r_t|h_t,z_t).
\]

虽 prior 简写为 `p(z_t|h_t)`，它仍是动作条件 prior：动作通过 `h_t` 进入。已读 PlaNet 式(4)及代码支持这个条件结构。recognition 的当前输出不能见未来观测；`h_t` 传递过去 sampled posterior latents 和动作，故 `q(z_t|h_t,o_t)` 是因果 filtering 的局部实现。它是近似推断，不自动等于精确 Bayesian belief，也不保证 `s_t^m` 是环境的充分统计量。训练序列整体记号里出现 `o_{1:T}`，不代表每个局部 q 使用 `o_{>t}`。[主文 §3](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf)

## 3. 生成、识别与标准 ELBO：可直接采用的推导骨架

`h_t` 总按上述递推消去；这样无需对不同 Dirac 变量做错误的 KL。给定动作，生成密度是

\[
p_\theta(o_{1:T},r_{1:T},z_{1:T}\mid a_{0:T-1})
=\prod_{t=1}^T p_\theta(z_t|h_t)p_\theta(o_t|h_t,z_t)p_\theta(r_t|h_t,z_t).
\]

识别分布是

\[
q_\phi(z_{1:T}\mid o_{1:T},a_{0:T-1})
=\prod_{t=1}^T q_\phi(z_t|h_t,o_t).
\]

右侧每个 `h_t` 都是所积同一 latent 历史 `z_{<t}` 和已知动作的函数；不是独立的常量，也不能把联合 q 写成各时刻边缘分布的独立乘积。`q_φ`标记局部recognition参数；由于h由θ递推，联合路径分布也可依赖θ，不表示与θ独立。缺失观测若选择q_t=p_θ，另有显式θ采样路径。识别分布在这里不读 reward，仍可为联合观测/奖励似然提供合法的变分下界，只是选择了受限 q 族。

因子化假设观测与奖励给定 `(h_t,z_t)` 条件独立，并给定动作而不建模动作的生成概率。令 `Y=(o_{1:T},r_{1:T})`，当 q 覆盖 `p(Y,z|a)` 的支持、相应期望存在时（本次正方差 Gaussian 满足支持要求）：

\[
\log p_\theta(Y|a)=\log\mathbb E_q[p_\theta(Y,z|a)/q_\phi(z|o,a)]
\geq \mathbb E_q[\log p_\theta(Y,z|a)-\log q_\phi(z|o,a)] = \mathcal L.
\]

展开 log-product，按 `z_<t` 条件分组，得到

\[
\mathcal L=\sum_{t=1}^T\mathbb E_{q(z_{<t})}\left\{
\mathbb E_{q_\phi(z_t|h_t,o_t)}[\log p_\theta(o_t|h_t,z_t)+\log p_\theta(r_t|h_t,z_t)]
-D_{\mathrm{KL}}[q_\phi(z_t|h_t,o_t)\Vert p_\theta(z_t|h_t)]\right\}.
\]

最小化负 ELBO 是三项的符号翻转。最大化的是数据 log-likelihood 的下界，不是“每步 posterior 和 prior 一模一样”。同时间 KL 在同一 posterior 历史产生的 `h_t` 上比较两个 stochastic 分布；它不比较 `q_t` 与 `q_{t-1}`，不比较当前 latent 与真实隐藏状态，也不是对采样点做距离。重建/奖励项与 KL 共同约束模型；KL 会影响 prior 与 recognition，不能笼统说只训练其中一侧。

此式由上述本次因子化独立推出；论文提供一般 SSM 观测项推导并说明 reward 类推（主文式(3)、附录式(8)）。不直接照搬论文简化的边缘 q 记号，以免隐藏历史耦合。[附录 F 式(8)](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)

若材料需要一个标量 Gaussian 核对题，可使用独立数学恒等式（方差 `v` 必須大于0）：

\[
D_{KL}[\mathcal N(\mu_q,v_q)\Vert\mathcal N(\mu_p,v_p)]
=\frac12\left[\log\frac{v_p}{v_q}+\frac{v_q+(\mu_q-\mu_p)^2}{v_p}-1\right].
\]

例如 `q=N(1,1/4), p=N(0,1)` 给出 `KL=0.818147...` nats。这是公式代入核验，不是 RSSM 训练实验。方差与标准差须在题面显式区分。

`β KL`、free nats、stop-gradient 或其他优化改动须另标为训练配方；不加说明不能仍称“由上述 Jensen 推导直接得到的标准 ELBO”。PlaNet Appendix A 的最终实现使用 free nats，故原文数学目标与工程损失也需分开说明。

## 4. 多步预测、overshooting 与规划须分开

从 `q(z_k|h_k,o_k)` 的样本和 `h_k` 出发，给定候选动作 `a_{k:k+H-1}`：

\[
\tilde h_{k+j}=f_\theta(\tilde h_{k+j-1},\tilde z_{k+j-1},a_{k+j-1}),\quad
\tilde z_{k+j}\sim p_\theta(z|\tilde h_{k+j}),\qquad j=1,\ldots,H.
\]

未来真实 `o` 未可见，因而不调用未来 recognition。可以解码未来观测用于诊断，规划回报仅需 reward head；PlaNet 规划不需要生成像素。单条 sampled rollout 是预测分布的一次样本，不是该分布；把均值反复送回非线性网络一般不等于多步期望。多步预测应在 `s^m=(h,z)` 上说明，不能假定 `z` 单独 Markov。[主文 §2–3](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf)

普通 rollout 是模型用法；latent overshooting 是额外训练关系。标准同时间 KL 直接比较一步 stochastic prior；这不表示标准 ELBO 没有历史梯度或全无跨时训练——h 的递推仍允许 BPTT，过去 posterior 样本仍参与未来项。overshooting 从较早 posterior 状态出发，沿多步 prior 链预测，再与目标时刻已有观测得到的 informed posterior 比较，不能每个中间步骤都偷读 observation。它也不同于把多步预测全部解码后再加 observation loss 的 observation overshooting。

严格引用论文时，式(5)先在一般 SSM 中把中间状态积分掉；式(6)/(7)实用 KL 在 prior rollout 到达的 penultimate state 上取外部期望，附录式(9)还使用一次 Jensen。不应把 `KL(q_t || exact d-step marginal)` 与 `E_rollout KL(q_t || last-step conditional prior)` 写成恒等式。RSSM 实用比较只在 stochastic 分布上进行，不能给含不同 deterministic Dirac `h` 的整个 joint state 直接写有限 KL。关于同一原模型 log-likelihood 的进一步关系，主文明确使用 conjecture，不适合作无条件已证定理。

原文 §4 和 Appendix D 特别限制：final PlaNet RSSM 并不需要 overshooting；Figure 8 报告所比较 RSSM 上略降、DRNN 上改善。教学应保留“用于改善某些模型的多步训练的候选正则”，不能承诺必然提升。[主文 §4](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf)，[附录 D、F](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)

## 5. MPC/CEM 与闭环接口

本次把 H 定义为动作个数，避免论文 `t:t+H` 的 inclusive 端点惯例造成 H 与 H+1 混用。候选动作是 `A=(a_t,...,a_{t+H-1})`，对应未来状态/奖励索引 `t+1,...,t+H`。可以使用无折扣有限回报

\[
J(A)=\mathbb E_{q(s_t^m),p_\theta}\sum_{j=1}^{H}r_{t+j}.
\]

`q(s_t^m)` 在此为模型路径变分分布诱导的 filtering 分布简写（`h_t`按同条随机历史构造）；它不是状态元组本身、精确环境 belief 或 CEM 的动作提议分布。

CEM 在本次给定的 reward objective 下反复采样动作序列、latent rollout 评分、取 elite、重拟合动作分布。它优化的是动作搜索分布，RSSM 参数训练是另一个更新过程。作者代码用 elite 的均值和 population variance 重拟合，标准差为 `sqrt(variance+1e-6)`；教学数值题可显式采用这个版本。源代码 horizon 是数组动作数；论文 Algorithm 2 的端点表达另一惯例。使用哪一个须在题面声明。[作者 CEM 代码](https://github.com/google-research/planet/blob/master/planet/control/planning.py)

MPC：用当前 belief 规划整段，实际只执行首动作；新观测到达后 filtering 更新，再重新规划。CEM 是可选的内层搜索器，MPC 是外层反馈执行方式。两者不是同义词；重复给定动作序列的开环 rollout 也不是闭环。

PlaNet 原始方案：每次重规划从零均值/单位方差重置搜索分布；论文中每个候选序列只采一条 latent trajectory，再求沿途预测 reward 的均值并求和。教学若为了显示期望使用更多 particles，必须标成自拟示范设定，而非声称复现原论文实现。单 trajectory 估计或有限 CEM 搜索不保证全局最优，也不保证消除模型误差。[主文 §2、附录 B Algorithm 2](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)

Dreamer 原论文训练 action/value 模型，利用潜空间想象轨迹和 value 梯度学习行为；这与 PlaNet 每次在线 CEM 搜索动作段不同。二者可以共用 RSSM 家族，不能把 world-model 的相近性说成控制器相同。Dreamer 原文 `p` 用于 representation，`q` 用于 imagined approximations；本单元维持 `p_θ` 生成、`q_φ`识别的约定，不交叉抄符号。[Dreamer §1–2、§4](https://arxiv.org/pdf/1912.01603)

## 6. 给材料与审查的风险清单

| 容易混绑的维度 | 必须保留的判断依据 |
|---|---|
| 环境 partial observability 与环境随机动力学 | 单帧不充分不证明真实动力学随机；同一观测对应不同隐藏状态已经构成需要历史/信念的理由 |
| deterministic h 与 stochastic z | h 用于可训练的历史记忆，z用于分布性表征；是结构与表达能力关系，不是“h=已知、z=未知”的硬切分 |
| conditioning past 与 smoothing future | 检查每个局部推断因子可见信息；训练片段完整可得不授予 online 推断访问未来 |
| ELBO、重建成功、多步校准、规划成功 | 分别属于目标定义、观测拟合、预测评估、控制评估；一项通过不能代替其余几项 |
| uncertainty 与 latent stddev | 正方差不自动是校准 uncertainty，更不自动分出 epistemic/aleatoric；本单元若没有额外建模不要扩张解释 |
| rollout、latent overshooting、CEM、MPC | 分别是预测操作、训练正则、动作搜索、反馈控制；每个都写清输入/更新对象/输出 |
| 观测解码与 reward head | 模型训练可能需要重建，潜空间候选评分不必解码图像；动作选择仍需要任务 reward objective |
| 连贯 toy 与论文实验 | 任何自拟数据、手设参数、精确 Bayes/Kalman 或枚举规划均标“机制示范”；它們不证明学出的 RSSM能达到相同性能 |

若用 Kalman/有限状态 toy，其 `exact posterior update` 是“预测分布→新证据→更新”的类比，不能写成 RSSM 的 amortized recognition 等式；若用真 RSSM 结构 toy，也要给 h/z prior/recognition/decoder/reward 完整接口、参数与贡献来源。若要把 uncertainty 影响决策作为认知要求，toy 必须包含在相同回报规则下由于信念差异而改变候选排序的实际对照；仅打印不同方差不足以承担该教学功能。

本文件完成的是技术范围和来源定位核验。任何实际图、交互、代码、题面和教师参考仍由材料职责按最终认知设计检查，不能以这些引用自动宣布成品教学功能已核。没有执行真实 RSSM训练、PlaNet复现或学习者测试。
