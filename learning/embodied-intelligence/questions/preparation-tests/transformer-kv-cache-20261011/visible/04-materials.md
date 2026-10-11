# 实际学习材料与连贯示范 / revision 1

身份：待审查备课输入，尚未作为正式教学呈现。允许分段使用；本文件不是学习者原答。文中的小数、张量与教师代码都是教学材料，不能转为用户已理解／已运行的证据。

## 1. 从一个新位置的工作看 Attention

考虑一个固定参数的因果 decoder。输入 token 经嵌入与位置处理成为向量，各层将当前位置的表示转成 Query、Key、Value。Query 用来向当前可见历史寻求相关信息，Key 参与匹配，Value 是被加权混合的向量。它们是学习到的表示；“键”和“值”并非把原文原封不动存进字典。[原 Transformer §3.2](https://arxiv.org/abs/1706.03762)。

对某层、某个 head，第 t 个位置的运算为

\[
s_{tj}=q_t k_j^\top/\sqrt{d_h}+m_{tj},\qquad
\alpha_{tj}=\frac{\exp(s_{tj})}{\sum_{r\le t}\exp(s_{tr})},\qquad
o_t=\sum_{j\le t}\alpha_{tj}v_j.
\]

合法历史位置的 m 为0，未来位置为−∞；等价布尔 mask 必须让非法项完全退出 softmax。把非法 score 乘0会令其变成0，exp(0)=1，仍然获得权重。多头把各头结果合并再投影，之后残差、逐位置归一化与 FFN 接到下一层；本单元只展开会影响缓存正确性的依赖。

全序列 Q 的行对应查询位置，K/V 的行对应可读取位置。一种常见逻辑布局：每层 K、V 各为 [B,H_kv,T,d_h]；Q 为 [B,H_q,q_len,d_h]。MHA 的 H_q=H_kv；GQA 每组多个 Query heads 使用同一 KV head。库的具体轴序可不同，语义与位置映射必须相同。

## 2. 一行完整示范：旧 KV 不变，新权重会变

为看清运算，给定一个单头的局部输入，d_h=1。这里直接给 Q/K/V，暂把投影当黑箱：历史 k=[1,0]，v=[2,6]；新增第3个位置的 q_3=ln2，k_3=1，v_3=10。

| 步骤 | 对象与操作 | 结果 |
|---|---|---|
| 读缓存并追加 | 保留 k_1,k_2,v_1,v_2，追加 k_3,v_3 | K=[1,0,1]，V=[2,6,10] |
| 新 Query 匹配 | ln2×[1,0,1]，缩放因子√1=1 | score=[ln2,0,ln2] |
| softmax | exp 得 [2,1,2]，总量为5 | α=[2/5,1/5,2/5] |
| 混合 Value | (2/5)×2+(1/5)×6+(2/5)×10 | o_3=6 |

无缓存版本若重算该完整前缀，再取第3行，只要得到同样的 q_3、K、V，就得到同一输出6。缓存版本节省历史 KV 的重新生成及历史位置的重复层计算；它仍计算新的 score、softmax 和 V 混合。

保持同一 q，假如只对旧两项算 attention，权重为 [2/3,1/3]，输出10/3。加入新项后，旧两项权重成为 [2/5,1/5]，不是直接沿用旧值。通常新位置的 q 也会变化；这里特意固定 q，隔离“softmax 分母改变”这一关系。旧 Query 的旧输出也没有被“改写”：它仍受其原来的因果可见范围约束。我们比较的是新查询行，不是让旧位置回头看未来。

本例只核一层一头的运算。两层代码使用另一组固定参数，负责让上下文化 K/V、位置及层间依赖可见；两者解释同一机制，数值不能跨模型混用。

## 3. 为什么高层的 KV 也能保留

令 h_i^0 为 token i 的嵌入及固定位置处理结果。第 l 层的 k_i^l、v_i^l 来自 h_i^{l−1}（含该层规定的逐位置归一化／位置变换）；高层输入已经包含前文信息，不只是静态词向量。

先固定模型权重、token 前缀、位置编号及位置算法、因果可见关系、逐位置运算和推理数值约定；关闭会引入不一致随机性的训练 dropout。追加 token 时：

1. 对旧 i，h_i^0 不变，因为 token 与位置没变。
2. 假设全部旧位置的第 l−1 层输入不变。该层旧 i 的 Q/K/V 不变；它依旧只能读取 j≤i 的相同 K/V，softmax 集合与 FFN 等操作相同，因此 h_i^l 不变。
3. 沿层归纳，所有旧位置的逐层 KV 不变。新 t 在第一层用第一层缓存求 h_t^1，再由它生成第二层新 Q/K/V，如此向上；每层各追加一行，得到与全前缀同一新位置输出。

这是理想确定性计算的等价理由；实际浮点运算因内核和累加顺序可能有小差别，要用恰当容差检查 logits。数学等价不承诺任何硬件上的 bitwise equality，缓存也不要求 Q 从来不存，而是标准自回归下一步无需历史 Q 来计算新行。

“只保存 token 嵌入便能替代所有层 cache”不成立。第二层 K/V 来自第一层的上下文化表示；少了逐层历史状态，仍需重新建立它们。细节可对照代码中的 layers、full_forward 和 append，以及教师运行摘要。

![两层因果依赖：高层KV来自上下文化状态](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/figures/two-layer-dependency.png)

图中箭头只表示允许的依赖，未标成实际attention权重。旧位置没有来自未来位置的箭头；新位置依赖可见前缀，因此旧状态保持与新状态计算能够同时成立。

## 4. 一条生成时间线

设 prompt=[A,B]。模型在 prefill 中同时处理这两项，但通过因果 mask 保持各位置的可见范围。

| 时刻 | 本次送入模型 | 完成后各层缓存位置 | 最后 logits 用途 |
|---|---|---|---|
| Prefill | A,B | A,B，长度2 | 预测第一个生成 token C |
| 选择 C 后 | 暂无新 forward | 仍为 A,B，长度2 | C 尚未因“被选择”自动入 cache |
| Decode 第一步 | C，位置2（从0编号） | A,B,C，长度3 | 预测下一 token D |
| Decode 第二步 | D，位置3 | A,B,C,D，长度4 | 预测下一 token E |

因此，生成 G 个输出 token 时，通常先由 prefill 选第一个，再处理 G−1 个生成 token 来预测余下输出；若要把最后输出也纳入缓存或继续预测，再送它一次。材料中的 N 专指 prefill 后实际送入模型的新增位置数，不偷偷把它与输出个数混成同一变量。[PagedAttention §2.2](https://arxiv.org/abs/2309.06180)。

![Prefill、Decode与Chunk的缓存时间线](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/figures/cache-timeline.png)

教师两层程序用prompt IDs [1,4,2]，随后固定送入[5,0,6,3]，对同一输入前缀分别执行完整路径和增量路径。下表是实际教师输出；固定续接ID用于保持比较对象，未从argmax取样。

| 本次模型输入 | 输入位置 | 两层cache长度 | logits预测位置 | 完整／增量logits最大差 |
|---|---|---|---|---:|
| [1,4,2] prefill | 0,1,2 | [3,3] | 3 | 0 |
| 5 | 3 | [4,4] | 4 | 0 |
| 0 | 4 | [5,5] | 5 | 0 |
| 6 | 5 | [6,6] | 6 | 0 |
| 3 | 6 | [7,7] | 7 | 0 |

各次旧KV保持原值，所有cache与全前缀对应值差也为0，容差1e−12。它是固定无训练toy的检查，不是生产模型准确率或硬件速度。[代码原件](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/code/transformer-kv-cache/preparation-r1/kv_cache_demo.py)、[逐步教师说明](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/teacher-run/numerical-walkthrough.md)和[实际结果](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/teacher-run/checks.json)可回查。不要求先安装库才能使用表中的关系。

若旧 cache 长度 P=3，一次追加两个 token，Q 有2行，K/V 有5行。它们的合法 mask 是

| 查询／Key 位置 | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 新位置3 | 可见 | 可见 | 可见 | 可见 | 遮住 |
| 新位置4 | 可见 | 可见 | 可见 | 可见 | 可见 |

判断式为 key_position≤query_absolute_position；普通2×5左上角 tril 若只允许首行第0列，会误遮历史。本单元不依赖某 API 的默认 is_causal 对齐约定，写清绝对位置后再核实现。

可复用前缀必须相同：同样的文字片段但不同之前上下文、位置、模型／adapter／位置变换不能直接当相同 KV。若0编号前缀位置r被改，r以前的有效缓存可保留；r及以后不能沿用旧状态，须按新前缀重建。固定逐位置嵌入的第一层可能有部分特例，但全模型有效前缀应按所有层成立，不能据特例批准整个后缀。

## 5. 节省什么，长历史仍付出什么

只比较固定层数与维度的普通 dense causal attention。Prefill 长P时有 Θ(P²H_qd_h) 的 attention 算术；投影与 FFN 还有对P线性的成本。Decode 新输入一行、当前可见长度T时，该行 attention 是 Θ(TH_qd_h)，新 Q/K/V 投影与 FFN 只做这一行。

定义无缓存基线为“每次重新运行整个增长前缀”，包含初始prefill的累计attention成本为 Θ(P²H_qd_h)+Σ_{r=1}^N Θ((P+r)²H_qd_h)。缓存路径为 Θ(P²H_qd_h)+Σ_{r=1}^N Θ((P+r)H_qd_h)，即 attention 部分 Θ((P²+NP+N²)H_qd_h)。N=0时两者均只做prefill。投影／FFN 的累计新位置工作也由重复全前缀降为处理P+N行。具体 head／层常数、算术精度和实现不同，不由这些式子推实测加速倍数。

缓存并没有把长上下文 decode 变成常数时间：新 Query 仍需读取本应可见的历史。逻辑 KV 读取规模随T增长；GQA 可以降低需要读取的不同 KV 数据量，但真实 HBM 流量还依赖内核复用、batch、布局等。显存带宽常是重要约束，但判断“本机就是带宽瓶颈”须有 profiling。小 Python 算例只统计逻辑工作，不测 GPU 吞吐。

教师程序按允许的因果 pair 实际计数，不计算被 mask 的上三角；普通密集矩阵内核可能仍执行相关算术。三角有效 pair、矩阵尺寸、真实 FLOPs 与墙钟时间分别解释。

## 6. 逻辑 KV 容量

每层每个位置有 K、V 两份向量；batch B、层数L、KV头数H_kv、每头维度d_h、每元素s字节：

\[
M_{KV}=2LBTH_{kv}d_hs\quad\text{bytes}.
\]

T 包含 prompt 和已送入模型的生成位置。若 batch 中有效长度不同，应按各请求 T_b 求和；矩形 padding／预分配可能按最大长度分配，实际容量还需查实现。1GiB=2³⁰ bytes。[GQA §2](https://arxiv.org/abs/2305.13245)。

主例 L=32，B=1，T=32768，H_q=32，d_h=128，fp16 的 s=2：

| 架构 | H_kv | 逻辑 KV | 对照的成立条件 |
|---|---:|---:|---|
| MHA | 32 | 16GiB | 每个 Query head 对应独立 KV head |
| GQA | 8 | 4GiB | 每组4个 Query heads 共享 KV |
| MQA | 1 | 0.5GiB | 全部 Query heads 共享一组 KV |

这张表比较三种架构的容量，不证明其相同质量或同一权重。现有 MHA 转 GQA/MQA 通常涉及模型权重转换／再训练和质量验证；不能删除几个 head 的缓存当作等价实现。

![不同KV头数的逻辑容量及双请求长上下文对照](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/figures/kv-capacity.png)

容量式未计权重、临时激活、attention workspace、页表、分配器碎片、量化比例因子、对齐与设备副本。因此“KV 低于卡容量”不足以判可运行。若量化到8bit，纯数据项s=1，但额外元数据与质量误差仍需计入；若 offload 到主存，GPU KV 压力可降，传输成本仍在。[HF 固定版本 Cache strategies](https://huggingface.co/docs/transformers/v4.57.1/en/kv_cache)。

## 7. 优化方案改变的对象

| 做法 | 实际改变／节省 | 成立条件和代价 |
|---|---|---|
| KV Cache | 复用已算出的逐层历史 KV，避免重复旧位置计算 | 需要有效前缀；容量随长度与并发增长 |
| FlashAttention | 对 exact dense attention 分块并合并 softmax，减少中间矩阵的 HBM 访问／物化 | 仍处理 dense 配对，算术量不会因此变为线性；不删除持久 KV；内核／硬件决定收益 |
| PagedAttention | KV 按块管理、逻辑到物理映射及合法共享，改善碎片与分配效率 | 单条唯一序列的逻辑 KV 数据量不因分页消失；共享要满足相同前缀状态，页管理也有开销 |
| GQA/MQA | 减少不同 KV heads 的数量 | 是模型结构选择，不能默认为原 MHA 语义等价；质量取决于训练／转换与用途 |
| KV 量化 | 降低数据字节数 | 有元数据、量化误差及内核成本；不能默认 logits 完全相同 |
| KV offload | 将部分缓存放主存等设备 | 传输和调度影响延迟，主存也有容量限制 |
| Sliding window／丢弃旧 KV | 减少可见历史或近似状态 | 原模型若本就规定窗口，可按原 mask 精确实现该模型；原 full attention 改为丢历史则改变依赖，不再等价 |
| RAG／摘要／压缩 | 改变送入模型的文本、选择外部证据或表示 | 可能省 token，但检索遗漏、摘要丢信息与生成质量须核；不等于持久 KV 管理 |

FlashAttention 与分页、GQA 等可以组合，因为它们作用的对象不同。组合是否有净收益要查实际内核、工作负载和资源，不以方案数量判断。[FlashAttention §3](https://arxiv.org/abs/2205.14135)，[PagedAttention §3–4](https://arxiv.org/abs/2309.06180)。

## 8. 长上下文推理需要三类不同证据

模型接受某个长度，是位置机制、训练分布与实现上限的问题。机器装得下并能处理，是容量与计算／传输问题。任务能可靠利用远处证据，是行为质量问题。KV Cache 解决重复运算的一部分，不能独自保证后两者，更不能改变模型已训练出的能力。

位置编号与位置变换也进入缓存条件：固定规则下相同 token 在不同位置未必有相同 key；若运行中更换 RoPE 配置或重编号，必须核旧缓存是否还对应新计算，不能只拼接shape。RoPE 等技术与长度外推的实际质量要按具体模型、配置和任务验证，不因出现某个位置编码公式就保证无限外推。

Lost in the Middle 在特定多文档问答和 key-value 检索任务、模型与设置中，检验相关信息位置和长度怎样影响表现；它提醒“存在上下文”与“可稳定利用”不同，不能把所有模型／任务都判定为同一 U 型。[论文 §2–4](https://arxiv.org/abs/2307.03172)。该论文的字符串 key-value 检索任务与 attention 的向量 K/V 不是同一个概念。

若真实任务是依据长操作日志解释一项机器人异常，应明确相关证据、干扰信息、必须跨片段连接的条件及答案核验。比较长度和位置时尽可能保持内容、模型、tokenization、生成设置和问题相同；记录实际正确性、引用依据、时延及资源。若同时换模型、上下文、检索策略和提示，单次提升无法确定是哪项造成。这个教学用途是离线推理说明，不证明机器人闭环效果。

供B4使用的一份具体离线材料如下。身份为AI构造的文书日志例子，用来备课；不是真实机器人日志或学习者记录。规则与当前快照共同定义本题，允许查阅。

```text
E1 / 规则版本 R3
本步骤的 permit 为 true，当且仅当：guard_closed=true，mode=manual，
并且 inspected_lot 与 ticket_lot 完全相同。检查采用下面E2的当前快照。

E2 / 当前快照
guard_closed=true；mode=manual；inspected_lot=L7；ticket_lot=L8。
```

固定问题：“依R3与当前快照，permit应为true还是false？分别引用规则与快照中相关字段说明。”可插入与这些字段无关的历史报表作为干扰材料；改变证据位置或干扰长度时保留E1/E2原文、版本、当前性及问题。Oracle输入只含E1/E2与这个问题，用于检查无长干扰时模型是否仍能完成该关系。这里的permit只是给定布尔规则的离线结论，不执行任何控制。它提供可核查例子，不强制新增一份回答任务。

本材料讲完后，连续任务将用已有公式与条件处理一个具体请求；不会要求逐段回复“继续”。本轮只交材料审查，请勿把这里的预备任务当用户已收到的正式作业。
