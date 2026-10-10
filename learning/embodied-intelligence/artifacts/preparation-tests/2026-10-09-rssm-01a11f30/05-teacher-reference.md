# W1 完整教师参考与反馈锚点

revision: 1；日期：2026-10-09。状态：prepared，仅供本次备课审查；不是学习者作答、盲评结果或掌握判断。

贡献：AI task-design agent 基于 01 的候选目标、02 的已核学科接口和 04 的人工题面独立展开；数值桥由父 agent 另作路径枚举核验。这里的“参考”表示给教师审完整原件所需的合法路线，不表示只有一种措辞或图法。完整参考若实际展示，即计为帮助与暴露，不能以随后复现宣称未提示成功。未进行神经模型训练、held-out prior 实验或真实控制测试。

符号统一：物理 $x_t$，模型 $(h_t,z_t)$，$h_1$ 给定、$t\ge2$ 递归；$a_t\to t+1$，$r_t$ 是到达 t 的奖励，reset 无 $r_1$；H 为动作数。动作条件联合中 $A=a_{1:T-1}$ 是已给输入。以下 $I_t^{o}=(o_{1:t},a_{1:t-1})$ 是所选因果 encoder 的观测／动作信息；环境可另提供奖励记录，但不因此改变这个 q 的输入定义。

## A—C．对象、数值桥和 RSSM 接口

同一红色不能决定当前隐藏状态或 posterior。桥中若红前 prior 为 $b$，红后为 $4b/(1+3b)$；$b=1/2$ 得 $4/5$，$b=1/5$ 得 $1/2$。观测 likelihood 一样，历史导致的 prior 不同。RSSM 的 h 压缩历史的确定递归，z 为随机 latent，q 根据当前 h 与观测产生近似推断。物理 x 是环境对象；这套表示通常既不保证精确 belief，也不保证可识别物理 x。功能对应是“把历史条件信息用于当前表示和预测”，不是 $b=h$、$b=z$ 或一个 z 样本等于完整 belief。

| 操作 | 合法输入 | 输出与仍未知项 |
|---|---|---|
| 递归到 t（t≥2） | 上一模型路径的 $h_{t-1},z_{t-1}$，实际／待评估的 $a_{t-1}$ | $h_t$；不需先取得当前 $o_t$，不识别 x |
| 当前推断 | 此历史的 $h_t$，已取得的真实 $o_t$ | $q_t(z_t\mid h_t,o_t)$；是所选近似 family，不宣称 exact posterior |
| 一步未来预测 | 当前表示分布／样本、候选 $a_t$、f 与 prior | $h_{t+1},p(z_{t+1}\mid h_{t+1})$；真实 $o_{t+1},r_{t+1},x_{t+1}$ 尚未知 |

桥的两个动作核分别对应 $P(H'\mid H),P(H'\mid L)=(0.9,0.1)$ 和 $(0.1,0.9)$。初始 reset 红后 $b_1=4/5$，固定候选未来无真实观测时：

| 候选 | 第一步 $P(H)$ | 第二步 $P(H)$ | 两步期望效用 |
|---|---:|---:|---:|
| SS | $37/50=0.74$ | $173/250=0.692$ | $179/125=1.432$ |
| SF | $37/50=0.74$ | $77/250=0.308$ | $131/125=1.048$ |
| FS | $13/50=0.26$ | $77/250=0.308$ | $71/125=0.568$ |
| FF | $13/50=0.26$ | $173/250=0.692$ | $119/125=0.952$ |

初轮 SS 为这四个候选的精确期望最优。$0.8\to0.74$ 只使用当前 belief 和 S 的转移，不使用尚未到来的蓝色 likelihood；当前并不知道环境之后一定返回蓝色。实际执行首 S、实际蓝色到来后，H 的未归一质量为 $(1/5)(37/50)=37/250$，L 为 $(4/5)(13/50)=52/250$，故总质量 $89/250$，更新 $b_2=37/89$。新证据改变条件信息，而不是 retroactively 证明初轮排序计算错。

| 新候选 | 第一步 $P(H)$ | 第二步 $P(H)$ | 两步期望效用 |
|---|---:|---:|---:|
| SS | $77/178$ | $397/890$ | $391/445\approx0.878651685$ |
| SF | $77/178$ | $493/890$ | $439/445\approx0.986516854$ |
| FS | $101/178$ | $493/890$ | $499/445\approx1.121348315$ |
| FF | $101/178$ | $397/890$ | $451/445\approx1.013483146$ |

新轮最优 FS，实际只执行其首 F；尾部 S 是这轮内部预测计划，下一实际观测后仍可替换。蓝色未到来时合法 belief 是 $37/50$，到来后才是 $37/89$；两侧保持相同转移与 likelihood，只改变信息可用性。

把 SS 首动作改为 F 后得到 FS：第一步由 .74 变为 .26；第二步同样使用 S 映射，得到 .308 而非 .692。原因是首动作改变了下一预测分布，再通过相同第二动作继续传播。神经 RSSM 对应的最早可能变化是 $h_{t+1}=f(h_t,z_t,a_t)$，继而是 prior、z、奖励头和后续递归；无权重时不能保证两 h 数值一定不同，也不能给变化方向或大小。

桥的 utility 是规划评价，不是提供给 filter 的实测奖励；若把实际 u(H/L) 观察到且它完全揭示状态，就需要把该新信息纳入 belief 更新，但本桥没有这种记录。桥没有 learned h、encoder、神经 decoder 或参数拟合；它以可精确核查的离散分布解释信息边界，不能承担神经 RSSM／ELBO 义务。

C 的局部切片在固定 $a_1$ 下给 $h_2=a_1-1$ 与 $a_1+1$。每条历史内 h 确定，跨随机 z 历史 h 有诱导分布；“确定递归”不等于“跨历史恒定”。不同 h 可以影响同一 o 下的 q，但依赖图不保证每种权重都产生不同输出。p 生成 latent／观测／奖励；q 以已可用观测近似推断 latent。训练似然中包含奖励而 q 不以奖励为输入是合法的 variational family 限制，不是下界失效，也不是所有 RSSM 都禁止 reward encoder。

## D．联合、q、Jensen、分解与 gap 的完整推导

固定 h1 与动作输入，代入递归 $h_t(z_{<t},A)$。$R_{\rm obs}$ 只包含实际取得的到达奖励。生成假设为给定 $(h_t,z_t)$ 后 observation 与 reward 头条件独立：

\[
p_\theta(O,R_{\rm obs},Z\mid A)
=\prod_{t=1}^T p_\theta(z_t\mid h_t)
p_\theta(o_t\mid h_t,z_t)
p_\theta(r_t\mid h_t,z_t)^{m_t}.\tag{J}
\]

$m_t=0$ 的 reward 已通过 $\int p(r_t\mid h_t,z_t)dr_t=1$ 边缘化；不是拟合“缺失奖励这个随机变量”，也不是把无记录的 reset reward 伪造为 0。若显式把确定递归序列 $h_{1:T}$ 列入 joint，需加确定递推的 Dirac 约束；这里已经代入它，不另算一个普通密度的 h-KL。动作是给定条件，不在本似然中拟合行为策略。

采用

\[
q_\phi(Z\mid O,A)=\prod_{t=1}^Tq_\phi(z_t\mid h_t(z_{<t},A),o_t).\tag{Q}
\]

左侧写完整 O 不等于第 t 因子输入未来 O；因子间还通过 sampled z 历史与 h 相连，不能把它当独立 $q(z_t)$ 的乘积。它也不等于 exact filtering posterior。

以下 importance 等式要求 q 在 joint 非零处具有支持；有限表达还需相应 log 比值和发射项可积。常用正密度 Gaussian family 可满足支持要求，但不能把这些条件默认为所有模型成立。若 q 的支持不足，首个 importance 等式不能原样写，仍可在合法的 $q\ll p(Z\mid O,R_{\rm obs},A)$ 等条件下从 KL gap 建立下界。

\[
\begin{aligned}
\log p_\theta(O,R_{\rm obs}\mid A)
&=\log\int p_\theta(O,R_{\rm obs},Z\mid A)dZ\\
&=\log E_q\left[\frac{p_\theta(O,R_{\rm obs},Z\mid A)}{q_\phi(Z\mid O,A)}\right]\\
&\ge E_q[\log p_\theta(O,R_{\rm obs},Z\mid A)-\log q_\phi(Z\mid O,A)]
\equiv\mathcal L.\tag{1}
\end{aligned}
\]

第二个连接是乘除 q 并按 q 积分；不等式是 log 凹函数的 Jensen。代入 J、Q，把乘积的 log 展成和，再用条件期望：

\[
\begin{aligned}
\mathcal L
=\sum_{t=1}^T E_{q(z_{<t}\mid O,A)}\Big[ E_{q_t}\big[
&\log p_\theta(o_t\mid h_t,z_t)
+m_t\log p_\theta(r_t\mid h_t,z_t)\\
&+\log p_\theta(z_t\mid h_t)-\log q_\phi(z_t\mid h_t,o_t)
\big]\Big].\tag{2}
\end{aligned}
\]

这里 $q_t=q_\phi(z_t\mid h_t,o_t)$，是在给定过去 sampled history 后的条件分布。对最后两个 log 项应用 KL 定义，得到

\[
\boxed{
\mathcal L=\sum_{t=1}^T E_{q(z_{<t}\mid O,A)}\left[
E_{q_t}[\log p_\theta(o_t\mid h_t,z_t)+m_t\log p_\theta(r_t\mid h_t,z_t)]
-\mathrm{KL}(q_t\Vert p_\theta(z_t\mid h_t))\right].}\tag{3}
\]

KL 方向 q 到 p、符号为负；发射对数似然在 q 下取期望，训练最小化其负值。各 t 的外层 history 期望不能一般省去，因为 h 随 z 历史变化；t=1 的 history 为空。写 $E_{q(Z)}$ 的紧凑共同记号也合法，相应项只依赖前缀。

令 $\pi(Z)=p_\theta(Z\mid O,R_{\rm obs},A)=p_\theta(O,R_{\rm obs},Z\mid A)/p_\theta(O,R_{\rm obs}\mid A)$。在支持、KL 与上述期望合法时：

\[
\begin{aligned}
\mathrm{KL}(q\Vert\pi)
&=E_q[\log q-\log p_\theta(O,R_{\rm obs},Z\mid A)]
+\log p_\theta(O,R_{\rm obs}\mid A)\\
&=\log p_\theta(O,R_{\rm obs}\mid A)-\mathcal L.\tag{4}
\end{aligned}
\]

这是完整序列 exact posterior 的 gap，包括后续观测和实际奖励对早期变量的影响；q 是 causal family 不会把 gap 自动改成逐时刻 filtering posterior 之和。整段训练损失可使用全部实际 O／R 并反传，未来 loss 会更新共享参数；这不等于某个前向 q_t 输入未来 observation。离线 smoothing 也可以是另一合法 q family，但其信息约定与当前在线 family 不同。

待审核简写稿应保留发射结构、恢复式 (3) 的 history 平均、将 KL 改为 $q\Vert p$、删除／mask reset 的虚构 reward、把 gap 改成式 (4)。如果明确“下面展示单条 sampled history 的 Monte Carlo loss 估计”，可用该条 h 写每步条件 KL，不再声称这是已经对全部随机历史平均的精确标量；这样省略记号是有声明的估计，而非消除随机对象。

对目标对照，令 $C_{\rm em}$ 为式 (3) 中所有发射期望，$K=\sum_tE_{q(z_{<t})}\mathrm{KL}(q_t\Vert p_t)\ge0$，则

\[
\mathcal L=C_{\rm em}-K,\quad
\mathcal L_{1/2}=\mathcal L+K/2,\quad
\mathcal L_2=\mathcal L-K.
\]

基础目标具有式 (4) 的原样 gap；另两者一般不等于它（K=0 的退化数值相同不改变定义）。在相同期望、非负有限 K 条件下，$\mathcal L_2\le\mathcal L\le\log p$，所以仍是较低下界，gap 为 $\mathrm{KL}(q\Vert\pi)+K$，不是原样式 (4)。$\mathcal L_{1/2}$ 没有一般下界保证：若 q 恰好为 exact posterior 且 K>0，则 $\mathcal L=\log p$，$\mathcal L_{1/2}>\log p$；即使某份数据上它恰巧仍低于 evidence，也不能推广。此对照只核数学地位，不证明任何 loss 版本控制更好。free nats、其他权重与 overshooting 要另写实际定义，不能自动继承本 gap；本题不要求 overshooting。

## E．限定候选下选用、拒用与两步传播

| 快照 | 核心接受 | 可选／条件使用 | 当前目标拒用 |
|---|---|---|---|
| E-a | 当前 q 初始化、f、future prior、reward head、候选比较 | decoder 生成预测 observation；CEM 与有限枚举择其一 | 带真实未来 o 的 future q；离线 smoothing 代替在线预测 |
| E-b | 实际首动作递归、已到达 o 的新 q、从新表示开始 f/prior/reward/搜索 | 展示新时刻 prior 以比较观测修正；新 r 可记日志／供后续训练 | 将旧候选尾部视作已经新规划；将 reward 悄悄作为本 q 新输入 |
| E-c | 明确另一个 q family 的离线 smoothing | 沿用生成模型／确定递归及其发射项 | 把其未来信息称在线当前过滤，或把其 informed path 分数称 future-prior 分数 |

E-a 从当前近似表示初始化。条件于当前一条历史，可取 $z_t\sim q_t$；若用完整表示分布／particles，应同时保留不同 sampled histories 所诱导的 h。对固定候选 A：

\[
\begin{array}{lll}
\widetilde h_{t+1}=f(\widetilde h_t,\widetilde z_t,a_t),&
\widetilde z_{t+1}\sim p(z\mid\widetilde h_{t+1}),&
\bar r_{t+1}=E_{p(r\mid\widetilde h_{t+1},\widetilde z_{t+1})}[r],\\
\widetilde h_{t+2}=f(\widetilde h_{t+1},\widetilde z_{t+1},a_{t+1}),&
\widetilde z_{t+2}\sim p(z\mid\widetilde h_{t+2}),&
\bar r_{t+2}=E_{p(r\mid\widetilde h_{t+2},\widetilde z_{t+2})}[r].
\end{array}\tag{5}
\]

两行未来真实 observation 均未取得，不调用其 q。预测 decoder 可以从路径生成 observation，但这只是模型产物；回灌它的另一个算法不新增真实证据，不是本基准轨迹。动作变化最早进入下一 h，再可能改变 prior、z、reward、后续 h；在参数未知时不推断改变的幅度、方向、具体数值或稳定性。

一般目标为 $V(A)=E_{\text{current approximation, future prior}}[r_{t+1}+r_{t+2}]$。单路径 $\bar r_{t+1}+\bar r_{t+2}$ 是其 sampled latent 估计，仍有估计误差；多粒子平均改善 Monte Carlo 估计，不自动修复模型。原 PlaNet 每候选用一条 latent 轨迹评分；多粒子说明是一般扩展。精确桥有限枚举在规定四候选和 H 内可以精确比较，不能据此称神经 CEM 全局最优。CEM 的搜索分布是动作序列 proposal，非 latent q；原算法执行最终 proposal 首动作均值，不必正好是某 sampled candidate 的首动作。

## F．运行记录的完整修订

N0 初始化、mask 合法。N1 在因果前向信息不变时让未来 loss 反传合法。N2 明示另一个离线目标和 family 合法，可保留为另实验。N3 当前递归与观测推断合法。当前预测路径的最早非法操作是 N4：所谓时刻 2 的未来预测使用了尚未到来的真实 o3、o4。即使这些帧在离线测试文件中可读，也不能作为部署时刻 2 候选的输入；如果明确任务改为 smoothing，那是另一条件下的合法估计，不能保留原预测标签。

从 N3 起，一个完整基准修订为：从当前 $(h_2,z_2)$ 近似初始化；对每候选 $a_2,a_3$，用 $h_3=f(h_2,z_2,a_2)$，取 $z_3\sim p(z_3\mid h_3)$，读预测 reward head 的 $\bar r_3$；再用 $h_4=f(h_3,z_3,a_3)$，取 $z_4\sim p(z_4\mid h_4)$，读 $\bar r_4$。此处不能把历史 z2 代入 h4 的上一 latent 输入，不能把先前已经到达的 r2 加入两未来动作的目标。按 $\bar r_3+\bar r_4$ 的规定估计和搜索选出候选，只执行首 $a_2^*$。环境实际返回 $o_3,r_3$ 后，使用实际执行的 $a_2^*$ 递归真实当前 h3，以真实 o3 形成 q3，再从此新近似状态评估新的两动作候选 $a_3,a_4$。新轮只执行首 a3，继续取得真实证据再重规划。

N4 修正改变预测分布及其评估含义；N5 修正改变第二步递归对象；N6 修正目标时间轴；N7 修正实际信息获取与行动接口。都可能改变分数／排序／选择，但无网络和实际分数不能断言具体动作一定改变。保留合法 offline training 和先前表示，不需要把整份记录全部作废。若选择只重命名 N7 为 open-loop 策略，其旧动作段执行可能作为另一策略存在，但仍未交付本题所选 MPC。

B1 在给定条件下合法。B2 虽正确过滤，却没有重评分，不能称已重规划。从 $37/89$ 的给定四候选中 FS 的 $499/445$ 最大，新轮执行首 F；该动作的未观测到达 prior 为 $101/178$。下一真实 observation 未给出，不能继续编 posterior 或声称随后一定执行 S。这是内部 fixed-action prediction 与外部 receding-horizon feedback 的连接；蓝后重算可以替换旧 SS 的剩余动作。

合法多解包括：用分布积分而非单 sampled 轨迹；以有限候选枚举而非 CEM 为规划内部机制；用连续文字而非表格；把合法 smoothing 独立命名保留；指出已给变量不足并保留未知。它们仍需保持当前信息、完整 $h,z$、reward 时间、execute-first 和新 q／新规划接口。若确实另设计了生成图像回灌或整段执行策略，可以说明另算法，但不能把它的结果冒称所选基准。没有独立环境数据时，修出合法流程不等于证明控制有效。

## G．条件与边界参考

G-a 的 action=0 数据无法区分两动态，它们对 action=1 的预测不同；不能从相同训练拟合或当前 latent posterior 很窄断言该候选预测可信，也不能据此指定两个模型谁为真。状态推断不确定性、模型条件过程／latent 随机性、有限采样误差、错设／参数不足／分布外预测误差分别处理。一个随机 RSSM 的 z 方差不是参数 posterior，不能自动给出校准 epistemic confidence。

G-b 保持版未来方差仍为 $1/4$，collapse 版为 0；都没有新 observation，故“无新观测→每步都更宽”并非一般结论。该条件明确改了 transition 假设，不能把反例的收缩数值赋给未指定权重的神经 RSSM。S/F 桥中的值也只能说明其核下的具体分布，不能推出所有模型单调性。

G-c 只能支持已报告的训练／teacher-forced 指标改善。是否 future-prior 好、未覆盖动作好、真实闭环回报好均未知；重规划提供修正机会，但有限 H、候选搜索、sampling 和模型误差仍在。一次固定动作序列比较没有对未来 observation 分支搜索 contingent policy，也不自动优化信息价值。ELBO 高、posterior 窄、图像重建好、流程／程序运行通分别不能保证物理识别、真实最优或稳定。这里需要保留未知，不把所有模型都断言无效。

## 一份可连续审查的 W1 端到端范答

我把 x 保留为真实环境的隐藏对象，用 $h,z$ 表示学习模型。h1 给定，a_t 作用到 t+1；o 和 r 是到达量，reset 无 r1。我不能由一张 observation 识别 x，因为同 likelihood 下不同历史 prior 可以形成不同 posterior；桥中相同红在 prior .5 和 .2 下分别给 .8 和 .5。神经模型用 h 组织历史、q 根据 h 和当前真实 o 推断 z，但这只是选定 family 的近似；不把 h 或一次 z 样本称精确 belief。条件于路径 h 的递归确定，不同 z 历史仍诱导不同 h，所以训练和表示期望要保留历史随机性。

在给定动作和初始化时，模型 joint 是 latent prior、observation emission 和实际 reward emission 的乘积；缺 reset reward 先边缘化，所选 q 是通过 h 相连的因果因子乘积。由合法支持下的 importance 等式和 Jensen 得到 E_q[log joint−log q]，再用条件期望分解为发射对数似然减去 E_history KL(q_t||p_t)。这条连接既保留 q→p 方向，也保留 h 的历史随机性，不再另写 h 的普通密度 KL。其 evidence gap 对照完整序列 posterior；future loss 可训练共享参数，但不因此把未来 observation 塞进在线 q。离线 smoothing 可另选 family，β 目标要与基础恒等式分开：β2 是更低下界，β1/2 没有一般下界保证。

实际当前时刻先由过去模型路径和执行动作递归 h_t，以已到达 o_t 得 q_t。比较两动作候选时从这个当前近似初始化，未来两步都递归 h、由 p 传播 z、读奖励头，真实未来 o 不在输入中；生成预测图像也不会新增证据。改变首动作最早可能在下一 h 起传播，具体幅度和方向需权重而这里没有。原单轨迹评分是期望估计；候选枚举／CEM 的比较对象是未来到达 reward 之和，H2 对应 r_{t+1}+r_{t+2}，不包含已经到达的 r_t，也不能重复使用旧 latent 作为下一步上一 latent。

我据此保留 N0—3 的合法操作，把 N4 起改为 future-prior 轨迹，把 h4 输入改为 z3，把目标改为 r3+r4，只执行选定首 a2。真实 o3 到来后再 q3、再规划 a3:a4。数值桥独立核了这个接口：红后从 .8 出发，SS 的1.432是四候选中最大；只执行首 S，真实蓝后 posterior37/89。新轮 FS 的499/445最大，因此现在执行首 F；未知下一 observation，不编未来 posterior，也不固执执行旧尾 S。桥是精确信息示范，不是 RSSM 实验或 ELBO 训练。

最后我把这条合法回路的结论限在给定模型、H、候选与信息条件。当前 posterior 窄不处理未知参数和未覆盖 action 的模型误差；无新 observation 的分布宽度可以保持或收缩；训练 ELBO／重建改善不保证 prior 或实际控制改善。MPC 会在真实新证据后重新比较固定序列，但这里没有证明 contingent policy 最优或真实稳定。公式、数据、标准示范由教师已给；我承担的是统一对象、连续推导理由、条件下模块映射与日志修订。若这些文字是直接读教师范答而得，不能另记为我无提示完成的学习证据。

## 反馈、合法限制与局部够用

反馈先对照实际原答与实际帮助，不预设学习者误概念。可用短句指向具体接口，例如：“这条 future 路径需要的是 prior；o3 尚未到来，把 N4 的 q3 换掉后再核奖励轴。”或“发射项保留，KL 改 q||p；h 随历史路径变化，外层平均还要补回。”纠正后把同一原件推进到下一个必要连接；不自动发换数字题或问继续。

| 原件中的实际缺口 | 最小必要反馈／支持返回 | 不能倒算的部分 |
|---|---|---|
| 对象或索引错 | 指出该式中的物理 x、模型 $h,z$、a_{t-1}→t；返回 W1.1／3 | 词表照抄不证明机制解释 |
| Bayes 算术遮住信息关系 | 给37/50、37/89及归一质量，返回 W1.3—5理由 | 未独立完成算术 |
| history 平均／gap 错 | 用06的两历史或KL定义补一处，返回W1.2连续式 | 同题修订不是新独立样本 |
| 模块会用但条件选择缺项 | 给实际o到达清单；返回W1.3／4条件映射 | 方法已给后的执行不证明未提示选法 |
| 局部预测对但行动接口错 | 指向首动作→真实o→q→新规划；返回W1.5—6 | 完整组织若由教师给，整体承担受限 |
| 参考／算例与程序不一致 | 先停用受影响锚点、核系统条件与内容 | 不要求学习者迎合错误参考 |

局部恢复到足以继续原连接就返回 W1，不要求更多轮同型练习。整体结论逐项核 G1—G6 与实际贡献，不把六教学维度揉成单一等级：可保留公式严格性而给算术，保留全部接口而收缩当前展开，允许查阅而要求理由，用表替图而不缩整体。没有学习者原件与帮助记录时，本文件只支持备课可审性。

事实定位：完整 joint／ELBO 与 filtering family 依据02§3—4对应的[PlaNet 正文第3—4页](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=3)和[补充第16页](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=16)；prior 展开、CEM与execute-first依据02§5—7的[正文第3—5页](https://proceedings.mlr.press/v97/hafner19a/hafner19a.pdf#page=3)和[补充第12页](https://proceedings.mlr.press/v97/hafner19a/hafner19a-supp.pdf#page=12)。上述推导、bridge、日志和反例是统一符号下的人工展开，不是来源原句、实测结果或学习者表现；未把新型RSSM、overshooting conjecture或实现代码列为本次已核。
