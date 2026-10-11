# AG2 独立机制与量化研究 / revision 1 / 2026-10-11

本文件仅为用户授权的测试备课材料与教师参考。未读取本单元既有备课记录；未搜索本学习目录旧主题资料。未开展真实教学、采集学习者表现或更改真实进度。职责为机制、成本、参数交互与可验证决策的专业依据；教学顺序由主设计者采用。数值情境是本次 AI 自制教学案例，不是真实设备实测。实际独立子 Agent 参与核查，但多模型一致不构成正确性证明。

## 1. 用途与核心问题

长期上下文推理需要保留可用语境，又受 GPU 容量、内存/互联带宽、并发、首 token 等待、逐 token 等待和任务质量共同约束。当前用途涉及的关键问题是：哪些计算可原样复用；剩下什么成本；一种优化改变了哪些条件；多项优化同时实施后是否仍成立；未知条件下怎样提出可被反证、更新的方案。

KV Cache 的作用是复用先前 token 在每层已经产生的 K、V，减少重复前向计算。它本身不增加模型训练时获得的长距离能力，也不免除新 query 对已保留 K、V 的读取和聚合。全文默认 decoder-only、全因果注意力、固定模型与配置、推理模式；特殊架构要另按实际 attention pattern 分层处理。

## 2. 从一行注意力到逐层缓存等价

列向量约定下，每层有 q_i=W_Q h_i、k_i=W_K h_i、v_i=W_V h_i；h_i 指该层输入，不能与所有层共用同一原始 embedding。矩阵注意力写成

\[
A=\operatorname{softmax}(QK^\top/\sqrt{d_k}+M),\qquad O=AV.
\]

允许连接 M=0，屏蔽连接 M=−∞；softmax 沿 key 轴逐 query 归一化。基础计算和 decoder 的 −∞ 因果屏蔽见 [Attention Is All You Need §3.2](https://arxiv.org/html/1706.03762v7)。HF 当前 cache explanation 页面把 mask 显示为乘法，故本材料不复制该式；其 [attention interface 的 float mask 表](https://huggingface.co/docs/transformers/attention_interface#pass-a-custom-4d-attention-mask)支持上面的加法写法。布尔、2D padding mask 与不同后端的 API 表示不可混用。

**严格等价的对象：**固定同一 token 前缀、位置、mask、权重和确定性逐位置运算时，cached 与重新计算全前缀的方法，在实数理想计算下得到同一最后位置的 hidden/logits。改变 kernel 或浮点归约顺序后不承诺 bitwise 相同；相同采样算法也不保证微小 logits 差异不会改变长串结果。正确性检查优先比较固定输入的 logits 和容差，再比较生成结果。

**逐层归纳：**

1. 基础层：旧 token 的 embedding、原逻辑位置及其他输入不变，故旧位置 h_i^(0) 不变。
2. 假设第 ℓ 层旧位置输入不变，则该层旧 K、V 和 Q 不变。对旧 query i，因果 mask 仍只允许 j≤i；新增位置完全被屏蔽，允许集合与归一化分母均不变。故该层旧 attention 输出不变。
3. 残差、标准按 token 的 LayerNorm/RMSNorm、MLP 等局部运算在旧位置上输入不变，故输出不变。结论推进到下一层。
4. 新位置的每层 Q、K、V 仍须由其当层输入计算；新 Q 读取该层旧缓存与新 K、V。旧 Q 不用于未来新 query 行，所以通常不长期缓存旧 Q。

这不是“hidden 从第一层到最后一层不变”；它是“在相同层、相同旧位置、相同前缀下，向末尾追加未来 token 不改变该旧位置的表示”。普通因果前缀性质与按层缓存的实现说明可参照 [HF How caching works](https://huggingface.co/docs/transformers/cache_explanation)。本处归纳是本次依据架构作出的推导。

**需共同成立的条件：**旧前缀 token 及次序不变；模型权重/adapter、tokenizer 得到的前缀和模型配置相同；推理时关闭 dropout 或随机过程已适当固定；每一层原允许的 key 集合、padding/packing 边界不变；每一层缓存完整且序列/批次身份映射正确；位置编码与相应逻辑位置不变；计算没有把序列统计或未来信息混入旧位置。缓存精度降低则是近似；同精度纯搬运、正确分页与完整保留可保留数学目标。

**RoPE 条件：**旋转后的 q_i=R(p_i)W_Q h_i、k_j=R(p_j)W_K h_j，有 q_i^T k_j=h_i^T W_Q^T R(p_j−p_i)W_K h_j。标准 RoPE 旋转结构见 [RoFormer §3.2，式 13–16](https://arxiv.org/html/2104.09864v5)。缓存常存已经旋转的 K；页地址/环形槽位并不是逻辑位置。删去前部缓存后把新 token 的位置擅自改为 0，通常改变相对角度。统一平移所有位置在纯 RoPE 下有额外等价可能，但须同步正确变换所有 Q/K 并满足其他位置条件，不能由“重编号”一词推断等价。若动态位置尺度随总长度改变，旧深层 hidden 的前向结果也可能变化；仅给旧 K 再旋转并不自动补回所有层的变化。

**反例边界：**取消 prefill 的因果 mask 后，旧位置可看到后继 prompt token；把这些 K、V 用作标准因果 decoder 缓存不能与标准完整前向等价。编辑前缀一个 token 后，编辑点及其后位置的多层缓存通常需失效；词面相同的后缀不等于相同前缀下的缓存。双向 encoder 追加 token 一般改变旧表示。原生窗口模型按其规则删除不再可见的缓存可保持该模型；给全注意力模型任意裁成窗口则改了模型运算。

## 3. 可连续跟踪的精确小算例

这是一个 attention 子层，不假装是完整语言模型。设 d_model=3、单头 d_k=d_v=1，W_Q/W_K/W_V 分别取输入向量的第一/二/三项；不给位置编码，缩放 √d_k=1。该层输入：

| 位置 | 输入 h_i=[q_i,k_i,v_i] | K | V |
|---|---|---|---|
| 1 | [1,0,2] | 0 | 2 |
| 2 | [1,ln 2,4] | ln 2 | 4 |
| 3 | [1,0,8] | 0 | 8 |
| 4（追加） | [2,ln 2,10] | ln 2 | 10 |

prefill 三位置：位置 3 的分数是 [0,ln 2,0]，权重 [1/4,1/2,1/4]，输出 4.5；缓存 K=[0,ln 2,0]、V=[2,4,8]。缓存保留的是 K、V，不是这一行权重。

输入位置 4 后：q_4=2、k_4=ln 2、v_4=10；append 得到四位置 K、V，分数 [0,ln 4,0,ln 4]，权重 [1/10,4/10,1/10,4/10]，输出 6.6。重新计算四位置完整因果注意力时，位置 4 的这一行也是 6.6；位置 3 仍屏蔽位置 4，其输出仍 4.5。此有限数值仅核对这一 attention 子层，不替代上面的全层归纳。

可由教师按主线采用的观察：新 query 行的旧列权重也会重新计算；旧 token 的 K/V 可复用；旧 query 行在 causal 重算中保持原结果；一层示范要由逐层连接才能解释整个 decoder。

## 4. 成本：一阶段、一 token 与完整生成分别计算

记 P=prompt token 数；生成 N 个 token 时 prefill 已给出第一个生成 token 的 logits，随后通常只有 D=N−1 次单 token decode；第 r 次 decode 处理位置长度 n=P+r，r=1…D。默认不再对最后输出 token 作不必要前向。设层数 L，query heads H_Q，KV heads H_KV，head dimension d，model dimension D_m；忽略常数和 softmax 次要项。

| 工作 | 注意力核心计算量（QK^T 与 AV） | 逐位置线性/MLP 工作 |
|---|---|---|
| prefill 全 P | Θ(L H_Q d P²) | 约 Θ(L P D_m²)，实际用 FFN 尺寸确定 |
| cached 单 token，已有长度约 n | Θ(L H_Q d n) | 约 Θ(L D_m²) |
| 朴素 no-cache，每步重跑长 n 全前缀 | Θ(L H_Q d n²) | 约 Θ(L n D_m²) |

缓存全生成注意力总量为 Θ(L H_Q d[P²+DP+D²])；朴素无缓存为 Θ(L H_Q d[NP²+PN²+N³])。它们是上述步骤求和，不是实测速度。cached **每 token** 的 attention 随 n 线性，完整生成总 attention 仍有二次项；prefill 仍二次。减少 H_KV 的 GQA 不把 H_Q 同比减少，注意力 query-key 配对数仍由 H_Q 决定；KV 投影、存储和可复用读取可减少，实际 kernel 是否物化 repeat-KV 影响收益。

严格手算对照：P=4096、N=1024、D=1023，按每层每个 query head 实际允许的因果 query-key 对计数：

\[
\text{cached}=\frac{P(P+1)}2+DP+\frac{D(D+1)}2=13{,}104{,}640,
\]

\[
\text{naive full-prefix}=\sum_{r=0}^{1023}\frac{(4096+r)(4097+r)}2=10{,}916{,}375{,}040.
\]

二者约为 833:1 **逻辑配对次数**，不得写成 833 倍实际加速。dense masked kernel 可能计算上三角后屏蔽、tiled kernel 可减少无效计算；权重/MLP、数据读取、kernel 效率、batching、mask 开销和首阶段都影响 wall time。

首 token 等待 TTFT 要注明是否含 queue、tokenization 与 prefill；逐 token ITL/TPOT 要注明定义、统计区间与 p95/p99，不能用平均整体 tokens/s 代替尾部服务体验。单请求 latency、系统总 throughput 和 admission/queueing 目标可以冲突。

## 5. 同一服务案例：从 raw KV 到组合方案

**自制情境：**固定已经训练好的 GQA checkpoint，L=32、H_Q=32、H_KV=8、d_k=d_v=128，KV 用 BF16（2 bytes/元素）；全因果、保留最长 32768 token 的 prompt+已处理生成长度。目标四路活跃请求。假设权重与其他必需内存扣除后，GPU 可给 cache 系统的总额为 12 GiB；其中再为 cache 管理、峰值变化等预留 1 GiB，raw KV 可用 11 GiB。这里的 12、1 是题目给定预算，非设备测量。实际部署须量峰值而非相信这一预留。

无共享、单份原始完整缓存：

\[
M_{KV}=L\sum_b T_b H_{KV}(d_k+d_v)s
=2 L H_{KV} d s\sum_b T_b.
\]

均长 C 路为 2 L C T H_KV d s。BF16 本例每 token 是 131072 bytes=128 KiB=0.125 MiB；一条 32768 token 为 4 GiB，四条为 16 GiB。每层 K/V 的典型形状为 [C,H_KV,T,d]，不应把 H_Q=32 填进 H_KV=8 的缓存式。层配置不同须逐层求和；混合原生窗口层应分别用各层真实保留长度。metadata、对齐、分配 slack、量化 scale、残留高精度区、跨设备复制不在 raw 式里。

| 条件/候选 | raw KV 教师参考 | 判断与需验证项 |
|---|---:|---|
| 4 路均到 32768 | 16 GiB | 超出 11 GiB raw 预算，正确分页不能消灭这些真实 token |
| 当前长度 [4096,8192,16384,32768] | 7.5 GiB | 按需分页目前可装下；不能由这一快照保证所有请求长到上限 |
| 最长长度固定、无共享时限制活跃并发 | floor(11/4)=2 路 | raw 容量可保证到 2 路；queue/throughput/SLO 是否满足仍未知 |
| native window 每层 8192、4 路 | 4 GiB | 只有检查点本来支持该 pattern 才可叫同模型等价；全 attention 裁窗须另验质量 |
| 理想 4-bit payload、4 路全长 | 4 GiB + 未知开销 | 1/4 只是 payload；量化误差、scale/residual、kernel latency 必须测 |
| 4 路有完全相同起始 8192-token 前缀，理想共享 | 16−3=13 GiB | 仍超 11 GiB；复制/部分末页还可加开销 |
| 4 路有完全相同起始 16384-token 前缀，理想共享 | 16−6=10 GiB | raw 有机会；需证明前缀身份/位置/模型与真实命中、保留策略和峰值 |
| 改成 H_KV=4 的其他检查点 | 2 GiB/全长请求，4 路 8 GiB | 更改了模型架构/检查点；不能声称当前训练模型的无损运行时开关 |

GQA 是 query 分组共享 KV heads；MHA→GQA 的论文方法需要 checkpoint 转换及后续训练，见 [GQA §2](https://arxiv.org/html/2305.13245v3)。本题已经固定 H_KV=8 的检查点；不能任意删除其中一半 KV heads，然后仍按原模型精确等价核验。

**分页手算：**页可容 16 token，raw 每页 2 MiB（本例跨层合计）。四请求最多浪费 4×15=60 token 槽位，raw 尾页浪费小于 8 MiB，另外有页表与分配器开销。若请求 [17,17,17,17]，16-token 页需 8 页、128 slots，对 68 live tokens 浪费 60 slots；页更大使短序列 slack 更大。分页可保留全部可见 token，却不降低每个 live token 的必要信息量。非连续 blocks、按需分配及共享的原理见 [PagedAttention §4.1–4.4](https://arxiv.org/html/2309.06180v1)。本材料的容量、页浪费与共享数值由上式自行推导，不将论文硬件结果转为本题实测。

## 6. 多项选择的联动，不逐项相加收益

| 联动 | 中间连接 | 有区分力的反例/失效条件 |
|---|---|---|
| 并发 × 保留长度 × 精度 × KV heads | raw 容量乘积；其他开销非简单乘积 | 加 4-bit 再增 4 倍并发，payload 又回原量，带宽/质量并未恢复原状态 |
| GQA × KV kernel | distinct KV 数据更少，多个 query heads 可共享读取 | 若实现物化重复 KV 或 kernel 未适配，理论4倍内存缩减不等于4倍总速度 |
| paging × admission/scheduling | 当前按需容量更高效、尾部增长仍需新增页 | 允许四长请求后全部增长，仍超 raw 预算；须 cap、reserve、preempt/recompute/offload 的触发规则 |
| paging × quantization | 页 payload 较小，scale/residual/packing 及kernel路径联动 | 不能照搬 BF16 16-token 页的 2 MiB 尺寸或假设任意软件实现兼容 |
| prefix sharing × window/eviction | 共享节省只来自实际保留且上下文相同的块 | 高命中静态同前缀资料不支持新工作负载；删除共享前缀使共享节省失效 |
| offload × 并发 × 长度 | 每步需回读的 CPU KV 增加；batch 可摊薄权重开销但增大cache读量 | GPU 容量成功而互联 ITL 超标；小块传输低有效带宽 |
| 压缩/裁剪 × 更高并发 | 内存可容更多请求 | 总 throughput 上升也可能使单请求 p95 更差，或删掉任务所需证据 |
| chunked prefill × decode SLO | 把 prefill 分段可改变调度干扰 | 不能只看隔离 decode 结果；混合长prefill与短decode时需测尾部延迟 |

最后一行是可检验的系统候选关系，非本轮实现核验；不能保证任何特定引擎/版本提供或达到该行为。原生窗口、量化、offload 的兼容性按实际版本检查，当前 [HF Cache strategies](https://huggingface.co/docs/transformers/kv_cache)给出了各类支持范围及 offload/量化权衡；这些 API 页是读取当日状态，没有本地安装与执行验证。

## 7. 带宽未知下的 CPU offload：先建界，再选试验

区分逐层 streaming offload 与暂停请求整体 swap。前者每个 decode step 从 CPU 取得相应层的旧 KV，后者只在被抢占/恢复时搬请求缓存；不能互相借用延迟估算。若 full attention 在 GPU 计算且一轮须传入四路全长 BF16 KV，本例 H2D 至少为 16 GiB/轮（忽略当前新增 token）。按给定实际流量 D_in 和有效 B_in，有

\[
t_{step}\ge D_{in}/B_{in}.
\]

这是至少一方向的容量界；不能因为“异步预取”把传输完全删除。若实现还每轮把整份更新后 KV 回传，D_out 也近 16 GiB。半双工/串行近似 t_transfer≈D_in/B_in+D_out/B_out；可完全重叠的全双工理想界至少 max(D_in/B_in,D_out/B_out)。只回传新增 token 的实现与回传整份缓存不同，题目必须写明流量。

| 有效 H2D 带宽（情境值，不是设备规格） | 16 GiB 单方向下界 | 双方向同带宽、串行近似 |
|---:|---:|---:|
| 16 GiB/s | 1 s/轮 | 2 s/轮 |
| 32 GiB/s | 0.5 s/轮 | 1 s/轮 |
| 64 GiB/s | 0.25 s/轮 | 0.5 s/轮 |

若 hard ITL 要求 100 ms/轮，单向至少需 160 GiB/s；若目前有效带宽未知，不能从“避免OOM”断言满足ITL。若实际 batch4 但某方向限32 GiB/s，这一流量假设下 500 ms 下界已直接排除 100 ms，无需再优化微小 compute。若只 offload部分层、降低并发、压缩传输或在 CPU 算 attention，则 D_in 与操作本身改变，应重建式子。

HF offload 文档说明逐层缓存转CPU并异步预取；[PagedAttention §7.3](https://arxiv.org/html/2309.06180v1)观察小块 swap 可损害有效传输带宽。这里的公式与敏感性数字是本次推导，不是上述文献的硬件结论。

## 8. 决策与优化的可核参考：允许信息不足

不能用“我选 paging+quant4+offload”作为第四层充分证据。可靠方案应把约束、假设、候选、辨别性试验和更新规则接成连续作品：

1. **约束与竞争目标**：是否固定当前 checkpoint 和 full attention；hard 32K 任务质量还是可接受近似；4是同时到达还是活跃decode数；TTFT/ITL与队列p95的硬阈值；GPU raw预算是否由真实峰值验证；成本/吞吐是次级优化目标还是硬约束。未知项保留变量或范围。
2. **先证明可排除项**：最坏四路 raw16 GiB大于11；paging不能单独保容量。cap2是容量候选却不能自动满足四路体验。若同前缀只有8K，共享到13仍不足。这样的推导限定选择空间，但不输出虚构最优。
3. **给出条件化候选**：固定模型、精度与全上下文优先可用 paging+cap2+queue，前提队列SLO允许；若必须四路且不允许近似，先看真实16K同前缀是否可10GiB共享，否则本硬件条件可能不可行。若允许质量近似，可评估quant4；若ITL宽松，可评估offload。未知带宽未测前不承诺offload。
4. **试验须能改变决定**：相同checkpoint、相同token输入、最长长度和混合长度，先测baseline→paging，判定分配/峰值影响；再仅改KV精度，判定质量及kernel延迟；在相同候选上改变并发2→4，判定容量、throughput及tail ITL；再测混合长prefill干扰和真实prefix命中。预算有限时优先测最可能淘汰候选的未知项。
5. **指标要匹配主张**：固定logits容差支撑缓存实现；最长/早中晚证据位置与需联合多片段的题支撑任务质量；peak allocated/reserved、CPU存量、实际H2D/D2H字节、方向有效带宽、transfer overlap支撑内存与offload；队列到达率、p95/p99 TTFT/ITL、完成请求数支撑服务体验。单个“needle找到”不证明所有长上下文质量，单个mean tok/s不证明tail SLO。
6. **更新/停止规则**：若quant4在目标题上达预设质量底线且峰值与tail满足，选其候选并记录条件；若质量下降，回退BF16、降低活跃并发或报告硬约束不可同时实现；若offload有效带宽低于必要界，淘汰此流量方案或重建分层/压缩方案；若共享命中低于预算阈值，按无共享 worst case控制接纳。没有实测即停在候选，不把预测写成已验证。

合法多解须由约束与结果支撑。预算可使部分候选暂缓；不要求把技术清单全部试一遍。第四层观察的是怎样在不完整证据下选择最有判别力的下一观察并据此调整，而不是学生有没有写出教师偏好的技术名。

## 9. 读取与核验范围

| 原件 | 本轮实际读取范围 | 已用于何处 | 未核范围 |
|---|---|---|---|
| [Attention Is All You Need v7](https://arxiv.org/html/1706.03762v7) | §3.1–3.5文字，attention与FFN公式；§4复杂度表文字 | mask、按位置运算、基本attention定义 | 没逐像素核对论文图；训练实验未审查 |
| [HF How caching works](https://huggingface.co/docs/transformers/cache_explanation) | Attention matrices、Cache class/storage、生成循环文字 | 每层cache、历史K/V、新query、合并长度 | 页面 mask乘法式不采用；无本地运行；不保证未来API |
| [HF v4.53.2 cache explanation](https://huggingface.co/docs/transformers/v4.53.2/cache_explanation) | 前半机制与公式、版本提示 | 交叉对照机制与版本边界 | 未用旧API制定可执行程序 |
| [HF Attention interface](https://huggingface.co/docs/transformers/attention_interface#pass-a-custom-4d-attention-mask) | backend简介、mask creation、custom4D mask表与语义 | float mask加法/布尔区分 | 无本地kernel或API执行；页面一处“0.0 masks”文字与前表相反，不采用该句 |
| [HF Cache strategies](https://huggingface.co/docs/transformers/kv_cache) | default/static、offload与quantized说明及兼容表 | 运行策略候选及速度内存权衡 | 未执行、未验证特定模型/设备兼容 |
| [GQA v3](https://arxiv.org/html/2305.13245v3) | §1–2与实验设置/表1文字 | Q与KV头区别、训练结构更改 | 未逐像素核对图；论文任务成绩不转成本题质量 |
| [RoFormer v5](https://arxiv.org/html/2104.09864v5) | §3.1–3.2公式11–16、相邻说明 | RoPE位置与旋转等价条件 | 未逐像素核对图；长距离衰减与全实验不作能力依据 |
| [PagedAttention v1](https://arxiv.org/html/2309.06180v1) | §2–4机制与memory/paging/共享、§7.1–7.3文字 | 按需页分配、共享、swap带宽边界 | v2 HTML打开失败，改读v1；不声称核全实验或当前vLLM实现 |

查阅日期2026-10-11。计算核验：精确小例按softmax指数手算代回；成本对prefix长度求和；容量、分页、共享、带宽数字用基本算术读回核对。没有真实GPU实验、真实课程作答、个体能力裁定。来源之外的变量模型和候选试验均明确为本次推导/教学情境。

## 10. 规范代码与教师实际数值核验

收到主设计者追加委派后，AI在规范代码目录编写 `code/kv-cache/test-prep-20261011-b/demo.py` 与同目录README，version1.0.0；实际以Python3.12.3运行，无第三方依赖、安装或计时。代码两层单头d=4、固定WQ/WK/WV、Q/K按逻辑位置RoPE、逐位置tanh残差；不是训练好的语言模型。结果保存并读回 `artifacts/test-prep/kv-cache-20261011-independent-b/teacher-check-output.json`。

代码SHA-256：`d5e3cb6c71ee9498685cd7bfe843c3c0ffdca69fbf48b1f7dd45ba8b0e111b93`。六个prefix的最后hidden及全部层K/V，完整重算与增量缓存误差均为0（许可1e−10）；改旧prefix却用stale cache、新token逻辑位置重置0、全attention删前两缓存位置的误差分别约0.151760、0.010892、0.109371，均实际显示本有限例的失效。容量公式亦在执行中断言BF16每token128KiB、四路32K=16GiB、FP8payload-only=8GiB，11GiB raw预算floor cap分别2与5。

此实际运行提供有限的教师参考数值，不是全称证明、真实GPU性能、FP8量化实现或学习者表现。原API文档核验范围仍为静态读取；未运行这些框架API。
