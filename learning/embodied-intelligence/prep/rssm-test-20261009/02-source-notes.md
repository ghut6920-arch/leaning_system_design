# RSSM 学科依据与教师核验笔记

备课测试稿；2026-10-09。不是学习者接触、作答、能力或进度记录。只读本次委派所需框架规则与公开原始来源；未读取其他学习记录。责任范围为学科与来源核验，认知目标与选法由认知设计稿决定。

## 1. 来源身份、位置、已读与未读范围

| 来源 | 固定定位 | 实际读取范围 | 允许支持的用途与限制 |
|---|---|---|---|
| Hafner et al., *Learning Latent Dynamics for Planning from Pixels*, ICML 2019，arXiv:1811.04551v5（2019-06-04） | [PMLR 主文](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf)；[含附录版](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)；[版本页](https://arxiv.org/abs/1811.04551v5) | §2 pp.2–3、§3 pp.3–4 Eq.(2)–(4)、§4 pp.4–6 Eq.(5)–(7)；Figure 2、3 captions；附录 A、B p.12 Algorithm 2；D p.14 Figure 8 caption；F p.16 Eq.(8)–(10)。读清文本与这些公式的文字抽取；公式另做下文独立推导。 | RSSM 定义、过滤推断、CEM/MPC、overshooting 的用途及最终 RSSM 版本的选择。未逐点核实验曲线、未复现实验、未核全篇参考文献。web screenshot 返回的是引用字符串，未取得图像可见内容，因此不声称逐箭头视觉核过原图。 |
| Hafner et al., *Dream to Control: Learning Behaviors by Latent Imagination*, ICLR 2020，arXiv:1912.01603 | [论文](https://arxiv.org/pdf/1912.01603)；[版本入口](https://arxiv.org/abs/1912.01603) | §2 Eq.(1)、§3 pp.3–5 Algorithm 1、Eq.(2)–(8)、Figure 3 caption；§4 pp.5–6 Eq.(9)–(10)。 | 对照 Dreamer v1 的行为学习与部署接口。未核 Dreamer v2/v3，未核 Atari 分支、对比学习分支、附录推导或性能曲线。 |
| Kingma & Welling, *Auto-Encoding Variational Bayes*, arXiv:1312.6114 | [论文](https://arxiv.org/pdf/1312.6114) | §2.2 p.3 Eq.(1)–(3)、§2.3 p.3 Eq.(4)–(5)、§2.4 的高斯重参数化段落。 | ELBO 恒等式、Jensen、重参数化的一般锚点。下文动作条件序列推导是本备课稿逐步推导，不冒充该论文的 RSSM 教材。 |
| 作者代码：PlaNet | [rssm.py](https://raw.githubusercontent.com/google-research/planet/master/planet/models/rssm.py) | 完整 132 行文本；重点 `_transition`、`_posterior`、`divergence_from_states`、`features_from_state`。 | 实现与符号映射：prior/posterior 共用更新后的 deterministic state；KL 在随机分布之间。只读 master 于本次检索的快照，未锁 commit、未安装 TensorFlow、未执行原代码；不是运行验证。 |
| 作者代码：Dreamer v1 | [models.py](https://raw.githubusercontent.com/danijar/dreamer/master/models.py) | `RSSM` 类（第 9–74 行），包括 observe/imagine、obs_step/img_step。 | 显示观测更新与无观测想象两个接口。只读 master 快照，未锁 commit、未运行；不能由此推出历史所有 release 的行为。 |

### 可直接采用的来源结论

PlaNet 的 Eq.(4) 将 latent 拆为确定性记忆与随机变量，过滤 encoder 在当前观测到来后更新随机变量。其在线控制用 CEM 搜索动作序列并执行首动作；下一观测到来后重规划。§4 与附录 A/D 明确最终 RSSM agent 无需 latent overshooting；d>1 的 posterior 目标停止梯度。[PlaNet 论文及附录](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf)

Dreamer v1 在模型想象轨迹上训练 actor/value，部署时从观测推断状态后调用 actor；其论文的 representation 分布写 **p**，imagined transition 写 **q**，与本稿常规变分符号相反。[Dreamer v1，§2–4](https://arxiv.org/pdf/1912.01603)

一般 ELBO 是联合模型对数密度减近似后验对数密度的期望，其与 log evidence 的差是近似后验到模型后验的 KL；高斯可用重参数化估计梯度。[AEVB，§2.2–2.4](https://arxiv.org/pdf/1312.6114)

## 2. 备课稿统一符号与最小语义

以下是为教学一致性选定的模型规格与推导，不把它称为上述论文的逐字原式。

| 对象 | 本稿符号与含义 | 不得混同 |
|---|---|---|
| 真实环境隐藏状态 | `x_t`，环境未完全暴露的状态 | 不是模型的 `z_t` 或 `h_t` |
| 观测与动作 | `o_t` 到来后选 `a_t`；`a_{t-1}` 影响 `o_t` | `a_t` 不可提前进入已发生的 `o_t` 推断 |
| 模型确定性记忆 | `h_t`，给定初态与过去 latent/action 路径后确定 | 路径未知时 `h_t` 的分布仍会变化；“deterministic”不等于“没有不确定性” |
| 模型随机 latent | `z_t` | 一个样本不等于分布；latent 坐标不保证是真状态坐标 |
| 生成 prior / transition | `p_θ(z_t|h_t)` | 当时还未使用 `o_t` |
| 近似过滤 posterior | `q_φ(z_t|h_t,o_t)` | 不声称等于真实环境 belief；也不自动等于模型精确 posterior |
| 完整模型状态 | `m_t=(h_t,z_t)` | 状态、该状态的分布、网络输出的分布参数是三个对象 |
| observation likelihood | `p_θ(o_t|h_t,z_t)` | decoder 提供训练信号；规划可以不生成未来图像 |

本稿统一 `p_θ=生成模型`、`q_φ=变分推断`。PlaNet 原文 stochastic `s_t` 映射为本稿 `z_t`；Dreamer v1 简写 `s_t` 是整体模型状态，其 `p(representation)` 映射为本稿 `q_φ`，其 `q(transition/observation/reward)` 映射为本稿 `p_θ`。引用时依据功能，不能只依据字母。

真实 belief 的定义可写 `b_t(x)=P_env(x_t=x|o_{≤t},a_{<t})`。RSSM 提供一个学习到的历史表示和近似 latent 分布；没有从该表示到环境真状态的已证明等价性时，只称“近似状态表示／latent belief”。POMDP 的 belief-MDP 与模型中的 Markov latent 也不能据同一术语认定相同。

## 3. 动作条件 RSSM 的过滤型序列 ELBO：完整独立推导

### 3.1 模型、时间与初态约定

取固定输入动作 `a_{1:T-1}`，模型在这些控制输入下生成序列；不拟合数据收集策略。`h_1=h_init` 固定。对 `t≥2`：

\[
h_t=f_θ(h_{t-1},z_{t-1},a_{t-1}).
\]

因此每条 `z_{<t}` 路径都有自己的 `h_t(z_{<t},a_{<t})`。首时刻不用虚构环境动作 `a_0`。等价实现也可固定 `(h_0,z_0)` 并用显式 dummy `a_0=0` 做一次初始化更新，但须说明它不是环境中执行过的动作。

生成模型与过滤变分族为：

\[
p_θ(o_{1:T},z_{1:T}\mid a_{1:T-1})
=\prod_{t=1}^{T}p_θ(z_t\mid h_t)\,p_θ(o_t\mid h_t,z_t),
\]

\[
q_{θ,φ}(z_{1:T}\mid o_{1:T},a_{1:T-1})
=\prod_{t=1}^{T}q_φ(z_t\mid h_t,o_t).
\]

`q` 写下标 `θ,φ` 是提醒 `h` 用到了 `f_θ`；常见简写仍写 `q_φ`。这不是独立的时间边际乘积：每个因子通过 `h_t` 依赖先前抽出的 `z_{<t}`。不用把 deterministic `h` 另拟一个高斯后再加入 KL。若增广为 `(h,z)` 联合过程，`h` 是共享递推上的 Dirac 约束；直接消去 `h` 最清楚。

### 3.2 从 evidence 到 Jensen

在所需密度与可积条件下，选 `q` 覆盖积分所需支撑，得：

\[
\begin{aligned}
\log p_θ(o_{1:T}\mid a)
&=\log\int q(z\mid o,a)\frac{p_θ(o,z\mid a)}{q(z\mid o,a)}\,dz\\
&=\log\mathbb E_q\left[\frac{p_θ(o,z\mid a)}{q(z\mid o,a)}\right]\\
&\ge\mathbb E_q\left[\log p_θ(o,z\mid a)-\log q(z\mid o,a)\right]
=\mathcal L.
\end{aligned}
\]

代入两个乘积的因子：

\[
\mathcal L=\sum_{t=1}^{T}\mathbb E_{q_{≤t}}
\left[\log p_θ(o_t\mid h_t,z_t)+\log p_θ(z_t\mid h_t)-\log q_φ(z_t\mid h_t,o_t)\right].
\]

令 `q_{<t}` 是前 `t−1` 个过滤因子组成的路径分布。先固定过去路径，内层对 `q_φ(z_t|h_t,o_t)` 积分，得到可逐步计算的形式：

\[
\boxed{
\mathcal L=
\sum_{t=1}^{T}\left\{
\mathbb E_{q_{≤t}}\left[\log p_θ(o_t\mid h_t,z_t)\right]
-\mathbb E_{q_{<t}}\left[
D_{\mathrm{KL}}\!\left(q_φ(z_t\mid h_t,o_t)\Vert p_θ(z_t\mid h_t)\right)
\right]\right\}.
}
\]

在 `t=1`，外层历史期望退化为空历史上的常数。`t≥2` 的 KL 即使能解析计算，也仍要对会改变 `h_t` 的历史路径取期望；不能拿一个平均 `h_t` 代入后声称与该期望等价。

差距恒等式是：

\[
\log p_θ(o_{1:T}\mid a)-\mathcal L
=D_{\mathrm{KL}}\left(q(z_{1:T}\mid o,a)\Vert p_θ(z_{1:T}\mid o_{1:T},a)\right)\ge0.
\]

这里右侧的目标是**完整序列的模型 posterior**。`q` 的因子不使用未来观测，是过滤型近似族；这不把右侧目标变成“每步真实过滤分布”。只有族包含模型 posterior 且找到它时 equality 才成立。模型 posterior 即便精确，也只是此模型中的后验，不等于真实环境 belief。

### 3.3 可选 reward 项与优化方向

本稿若需要 reward，统一选 `r_t` 为到达时刻 `t` 的 reward，并声明 `r_{t+1}` 与 `a_t` 引发的转移对齐。增加 `p_θ(r_t|h_t,z_t)` 时，在重建期望内再加 `log p_θ(r_t|h_t,z_t)`。`q` 仍可只读 `o`；它是合法但可能较受限的变分族，gap 目标需变成 `p_θ(z_{1:T}|o_{1:T},r_{1:T},a)`。

若材料用 API 的 `env.step(a_t) -> (o_{t+1},reward_t)`，把 API `reward_t` 明确重命名为本稿 `r_{t+1}`，或全稿改另一套 reward 下标。两套都合法，禁止静默切换。

训练可最大化 `L` 或最小化 `−L`。一般 `β≠1`、free-nats clipping、额外 overshooting 项属于改造目标；不自动称其就是上式原数据 likelihood 的标准 ELBO。高斯 `z=μ+σ⊙ε`、`ε∼N(0,I)` 支持采样路径的重参数化梯度；不证明优化能找到全局解。

## 4. 从过滤训练到多步预测及闭环控制的接口核验

训练路径在每时刻使用真实当前观测形成 `q` 样本，并用该样本更新下一步记忆。此时 prior 与 posterior 共用由同一过去路径得到的 `h_t`，可计算逐步 KL。

从当前时刻 `t` 预测未来时，先依据实际历史得到初始 latent 分布。对候选动作 `u_{t:t+H-1}`：

\[
m_t\sim q_t,\qquad
h_{t+k}=f(h_{t+k-1},z_{t+k-1},u_{t+k-1}),\quad
z_{t+k}\sim p_θ(z_{t+k}\mid h_{t+k}),\quad k=1,\ldots,H.
\]

未来 `o_{t+1:t+H}` 不存在于执行时输入里；可以由 decoder **预测**，但不能用数据集未来观测做 posterior 校正后仍称 free rollout。中间随机路径应积分或 Monte Carlo 抽样；均值轨迹只是特定近似，一般非线性模型里 `f(E[z])≠E[f(z)]`，奖励在均值处也不一般等于期望奖励。

例如用到达 reward 下标的候选目标：

\[
J(u)=\mathbb E_{q_t,\,p_θ\ \mathrm{rollout}}
\left[\sum_{k=1}^{H}\gamma^{k-1}\bar r_θ(m_{t+k})\right].
\]

候选得分、选择动作、观察环境、重新推断是不同接口。有限预算的候选优化不保证全局最优；模型期望 reward 不保证真实 reward。闭环 MPC 为：当前 posterior → 评估候选 rollout → 执行首动作 → 实际新观测 → 当前 posterior 更新 → 重规划。普通 MPC 的候选是开环动作序列，而整个部署控制回路是闭环；二者不矛盾。

### latent overshooting 的安全讲法

本稿仅将它作为可选支持分支：从较早 posterior 初始化，跳过中间真实观测，沿 prior 预测到更晚时刻，与该时刻依完整已知训练历史得到的 posterior 做 latent 一致性约束。终点 posterior 可作为训练目标；它不是候选 rollout 的输入。

不可把“KL 到混合后的多步 marginal”与“对 intermediate prior 路径取期望的条件 Gaussian KL”当作同一表达。原文 Eq.(6)–(9) 还使用了将 log 移入多步 prior 期望的 Jensen 步骤；若教学只给路径近似的一致性损失，就明确称 auxiliary regularizer。原文对多步 predictive distribution 的 bound 与原始 one-step likelihood 的关系使用 conjecture；不得升级成不加条件的已证定理。

## 5. 必须分开的维度与教师检查点

| 维度 A | 维度 B | 最小检查 |
|---|---|---|
| 真环境 state/belief | 学到的 latent state/distribution | 同一观测不等于同一真状态；latent 精确推断也不证明世界模型正确 |
| `h` 条件确定性 | `z` 条件随机性 | 不能直接命名成“h=已知，z=未知”；过去 z 变化也改变未来 h |
| prior / posterior 的信息条件 | one-step / multi-step 的预测距离 | 一步 posterior 不是一步生成 transition；多步 prior 也不使用中间真实 o |
| filtering / smoothing 近似族 | train / deploy | 训练可用 smoothing，但在线输入限制仍是过滤；本次选 filtering，须解释其序列 joint |
| latent stochasticity | epistemic model uncertainty | 单个 Gaussian RSSM 的方差不自动覆盖参数不确定性或 OOD 风险 |
| 生成模型训练 | 行为／规划优化 | ELBO 不直接优化控制回报；CEM、actor/value 是不同控制选法 |
| 单次规划内部的开环 rollout | 实际控制的闭环重规划 | 候选长序列只实施第一动作，然后用真实观测刷新 |
| 数值代回、代码运行 | 一般数学正确性、经验性能 | 彼此分别给证据；不能用 toy 算对证明实际图像系统性能 |

## 6. 可用于材料核验的数值锚点（自拟，非论文实验）

下面只是检查公式、符号和期望的独立锚点，不替认知设计者指定活动。

1. 一维高斯：`q=N(1,0.25)`、`p=N(0,1)`（第二参数为**方差**），应有
   `KL(q||p)=0.5[log(1/0.25)+(0.25+1)/1−1]=0.818147...`。
   `KL(q||q)=0`；写反 `KL(p||q)` 通常不同。
2. 设 decoder `o|z∼N(z,0.25)`、当前 `o=1`，上面的 q 有
   `E_q log p(o|z)=−0.5[log(2π·0.25)+(0.25+(1−1)^2)/0.25]=−0.725791...`。
   忽略 q 方差、仅在均值处评价，错误地高估重建项 0.5。
3. 此单步边界模型 `p(o)=N(0,1.25)`，因此 `log p(o=1)=−1.430510...`；`L=−1.543938...`，差 `0.113428...` 等于到精确 posterior `N(0.8,0.2)` 的 KL。它核的是 ELBO 下界及 gap，不证明 RSSM 多步性能。
4. 数值 RSSM 若 `h_{t+1}=αh_t+z_t+a_t`，要分别报告 conditioning-on-one-history 的 prior 参数与对所有 q 历史混合后的 marginal；把两者都叫 `prior variance` 会掩盖条件差异。多步 reward 若含平方，例如 `−z²`，用 `−(μ²+σ²)`，不能只用 `−μ²`。

上述算术已手工逐项重算；未声称执行代码验证。若材料产物采用不同 toy 参数，必须重新核它实际参数、轨迹、reward 和问题参考。

## 7. 来源阶段的可采用范围与剩余边界（后续成品审查见 8–9）

可用于本次备课的完整主线：动作时序 → 部分可观测与历史表示 → RSSM 两路径和信息条件 → 过滤型联合变分族 → Jensen/逐步 ELBO → 观测驱动训练与无未来观测 rollout 的区别 → 候选回报 → 单动作执行与重规划。教师需依据具体材料逐题检查，而不是凭来源核验清单宣布本次问题合格。

仍未核：实际材料文件的算例、图／可视化成品、问题充分性与合法多解、Encoding/Post-Encoding 暴露边界；由材料制作与审查阶段完成。未运行作者神经模型或图像环境，也不提交学习进度、目标通过或掌握结论。

## 8. 已完成的教师 toy 数学审查

审查对象为 [verify_toy.py](../../code/rssm-test-20261009/verify_toy.py)，AI 编写的 `teacher-toy-v1`。本责任者实际回读完整代码并用 Python 3.12.3 执行，exit code 0；源码 SHA256 为 `EF50F8FE14F804A30404A38D897FAEEC9D89A800BC224E77B3503B33823F0432`。代码变动后此定位须重核，不能把本结果自动贴给其他版本。本次审查未改该代码。

### 8.1 规格与解析 ELBO

代码采用 `h_1=0`、`h_t=.5h_{t-1}+.5z_{t-1}+a_{t-1}`，`p(z_t|h_t)=N(h_t,1)`，`p(o_t|z_t)=N(z_t,.25)`，`q(z_t|h_t,o_t)=N(.2h_t+.8o_t,.2)`；观测 `(1,1.5,.7)`、历史动作 `(.5,−.5)`，高斯第二参数均为方差。

令 `M_h,V_h,M_z,V_z,C_hz` 为 q 路径下的均值、方差与协方差。代码的 q 历史传播符合：

\[
M'_h=.5M_h+.5M_z+a,\qquad
V'_h=.25(V_h+2C_{hz}+V_z),
\]

\[
M'_z=.2M'_h+.8o,\quad V'_z=.04V'_h+.2,\quad C'_{hz}=.2V'_h.
\]

对 `h` 的条件高斯 KL 内部，`μ_q−μ_p=.8(o−h)`，所以外层期望中应出现 `.64[(o−M_h)²+V_h]`。`exact_variational_elbo` 正确保留该项和重建的 `V_z`，没有将完整 q 期望替换成均值轨迹代入。

| t | E_q h | Var_q h | E_q z | Var_q z | E_q log p(o_t|z_t) | E_q KL |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | .8 | .2 | −.705791352645 | .724718956217 |
| 2 | .9 | .05 | 1.38 | .202 | −.658591352645 | .535918956217 |
| 3 | .64 | .068 | .688 | .20272 | −.631519352645 | .427630956217 |

总 `L=−3.684170926585333`。t=3 的 `Cov_q(h,z)=.0136`；t=2 为 `.01`。

### 8.2 独立 generative likelihood 路线

`exact_log_evidence` 不使用 q 网络的 `.2h+.8o` 规则，而把 `(h,z)` 作为二维线性高斯状态。转移矩阵与过程噪声为：

\[
A=\begin{bmatrix}.5&.5\\.5&.5\end{bmatrix},\quad
b(a)=\begin{bmatrix}a\\a\end{bmatrix},\quad
Q=\begin{bmatrix}0&0\\0&1\end{bmatrix},\quad
o=[0\ 1](h,z)^\top+\nu,\quad Var(\nu)=.25.
\]

代码的 prediction covariance 是 `AΣAᵀ+Q`。innovation variance 是 `V_z+.25`；`K_h=C_hz/S`、`K_z=V_z/S`；三个 covariance 更新用同一步的旧值同步赋值，符合 Kalman 更新。初态 `h_1=0,z_1∼N(0,1)` 与模型一致。

故此线性 toy 的精确 log evidence 为 `−3.6766345938409453`，与解析 q ELBO 差 `0.007536332744387586≥0`。这检查了完整序列的下界；不是神经 RSSM 参数拟合或现实经验性能的证明。精确模型过滤可以用当前观测更新对 `h` 的不确定性认识；此 q 族的 `h` 仅由过去抽样路径递推，不能因某一步条件 q 为局部 conjugate posterior 就称它等于全序列精确 posterior。

### 8.3 条件 root 规划与再次锚定的边界

规划代码采用**固定 `h_3=.64` 的条件 root**：`z_3∼N(.688,.2)`。完整 q 的 root 则有 `Var(h_3)=.068,Var(z_3)=.20272,Cov=.0136`。二者均值相同，联合不确定性不同，必须在题面和教师参考中明说。

`rollout` 不接收未来观测；每步使用 `AΣAᵀ+Q` 保留 root 随机性、transition noise 及 h/z covariance。两步 `Var(z)=1.05,1.3` 正确，`E[(z−1)²]=[E(z)−1]²+Var(z)` 的 cost 实现正确。离散候选域 `{−.5,0,.5}²` 上最小 expected cost 为 `2.428792`，唯一最优序列 `(.5,0)`；这叫枚举候选 MPC，不称执行 CEM 或连续动作全局最优。

闭环示范另取 `z_3=.688` 的**均值路径锚点**更新 `h_4=1.164`，作为新观测的教学给定输入为 `o_4=−.5`，在固定 `h_4` 下条件 q 为 `N(−.1672,.2)`；重新两步枚举最优仍为 `(.5,0)`，因此当前首动作 `.5` 与先前未执行的后缀 `0` 不同。它正确展示了“只实施首动作，再根据新观测重规划”的接口。

这次 `h_4` 再次固定，是示范选择的支架。若连续传播上一步的条件 root，不重新锚定 h，`Var(h_4)=.05`，该 q 更新后的 marginal `Var(z_4)=.202,Cov(h_4,z_4)=.01`，而非表中的条件 `.2`。因此不能把 `.2` 声称为完整历史 posterior 的边际方差，或把 `h_4` 均值锚点声称为实际观察到的 latent。一般 `(h,z)` root 的规划目标须对联合分布积分／抽样。

此支架不妨碍入门用途，条件是：先明确条件 root；把代表性路径、整条 q 期望、候选 rollout 三种运算分开；整体工作再要求指出恢复联合 root 后要改哪些期望／抽样接口。它能证明本 toy 的数值与接口自洽，不能单独提供“完整 belief-MPC 已会做”的证据。`representative_trace` 的 h/z 均值在这个线性 toy 恰等于 E_q；一般非线性 RSSM 不具有这一便利。

代码中的 variance/下界/改动作断言已通过。实际材料展示与题目语义仍需材料成品审查；没有把脚本通过等同于教学设计通过。

## 9. 核心材料与 W1/W3 情境核验

已实际读取 `03-core-materials.md`、`04-learner-work.md` 修订1全文，以及更新后脚本完整文本与 `09-numerical-check.json` 的本次输出。脚本新增 `work_scenario` 后当前 SHA256 为 `562123DD23CDCE0CE11F8426A27091847004A592600FA8A4175383DED1A8CBE9`；重新以 Python 3.12.3 执行成功。§8 的原 hash 保留为前次审查定位，当前两份工作情境按本段 hash。

### 已核公式与信息条件

- M3 的 controlled-input 约定、joint 因子、过滤路径 q、Jensen、KL 方向及外层路径期望、完整序列 posterior gap 与 reward 下标符合 §3 的独立推导。行为策略项与控制输入 likelihood 已区分，未以数据里的 action conditioning 保证任意离线外推。
- M4.2 的完整 q 期望与表中均值／方差／KL／log evidence 全部符合实际计算；M4.3 与规格页明确区分完整 joint root 和固定 h 的条件 root，未把 `.2` 当作完整 q 的边际 z 方差。
- M4.4 明确 `h_4` 再次锚定、真实新观测输入与想象均值分离；这份手算控制器的近似已经显示，不称精确 belief-MPC。W1/W3 使用同一近似，接口连续。
- 指定 cost 由任务提供，未宣称从 observation ELBO 学出。枚举候选控制没有冒充 CEM，实现 root 与抽样路径之别没有冒充真状态 belief。

### 新情境逐项结果

下表结果已对照四张完整九候选表，所有单元格吻合至题面舍入精度；再分别以平方期望公式手核最优候选。

| 项目 | W1 | W3 |
|---|---|---|
| 前缀 o；历史 a | `(.5,0,−.2)`；`(0,.5)` | `(.2,.9,−.4)`；`(−.5,.5)` |
| 代表性 `h_2,z_2` | `.2,.04` | `−.42,.636` |
| 条件 root `h_3；μ(z_3),v(z_3)` | `.62；−.036,.2` | `.608；−.1984,.2` |
| 首轮唯一最优序列；cost | `(.5,0)`；`2.461528` | `(.5,.5)`；`2.52908608` |
| 教学给定 `o_4`；再次锚定 `h_4` | `−1；.792` | `−.8；.7048` |
| 当前条件 q_4 的均值、方差 | `−.6416,.2` | `−.49904,.2` |
| 第二轮唯一最优序列；cost | `(.5,.5)`；`2.58611008` | `(.5,.5)`；`2.5682885888` |
| 新首动作 vs 旧未执行后缀 | `.5 ≠ 0` | `.5 = .5` |
| 完整 q ELBO | `−3.5236909265853327` | `−4.258116526585333` |
| 精确模型 log evidence | `−3.505101747125617` | `−4.232838973402989` |
| gap | `.0185891794597155` | `.025277553182343482` |

例如 W1 首轮 `(.5,0)` 的两步均值都是 `.792`，期望成本 `2(.792−1)²+1.05+1.30+.1(.5)²=2.461528`。W3 首轮 `(.5,.5)` 的两步均值 `.7048,1.2048`，成本 `(.7048−1)²+(1.2048−1)²+1.05+1.30+.1[(.5)²+(.5)²]=2.52908608`。第二轮 W1 均值 `.5752,1.0752`，W3 `.60288,1.10288`，对应上表 cost。W3 特别支持“重新规划不必改动作”的条件辨认，不能将“动作变化”设为闭环本身的必要证据。

### 定位并已核更正

M4.1 前缀表原先用 `...+a_1=.5`、`...+a_2=−.5` 将动作赋值和整个 h 表达式绑定，容易读成相互矛盾的 h 等式。材料责任者收到定位后已改为完整数值运算并独立标注动作；本责任者实际读回确认了第 139–140 行更正。演示执行与新观测已标为教学情境中的假设执行和给定反馈，避免冒充实际环境实验。

M2 当前 Mermaid 画的是有观测更新分支，prior 节点没有直接抽样到 z 的边；已建议材料责任者在图前补充该边的文字接口说明，或标出无观测时改用 prior，避免读者把 q 视为唯一 z 来源。M4 无观测公式本身正确。

### 仍需下一阶段审查

本段不将以下工作标为完成：05 教师参考的多解与条件分支、06 支持调用的潜在代做、07 首回复与题面的暴露边界、Mermaid 实际渲染效果。04 的 A/B/C 对照在定义层面可辨：B 线上读到尚未来的 archive o；C 可有离线平滑用途而无权作为 t=3 线上根，具体误差因平滑族未给而无法数值判断。教师参考还应说明档案未来观测绑定对应已执行动作，不能把同一未来观测拿来给不同候选做 counterfactual 打分。没有从这些检查形成任何真实学习进度或能力结论。
