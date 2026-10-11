# KV Cache 与长上下文推理：独立学科研究交接

日期：2026-10-11（Asia/Shanghai）。用途：本次测试备课的 AG2 学科依据，供主入口转换成完整认知主线、材料和教师参考。本文没有正式教学，没有真实作答、能力诊断或进度变更。未搜索、打开或复用本单元既有备课记录。

## 1. 从用途提出专业问题

本单元的实际问题是：在同一生成服务中，怎样让足够长的输入和输出可计算、可存储、可及时返回，同时仍支持所需的证据使用与推理？“可装入”“可完成生成”“能利用远处证据”“达到延迟/吞吐目标”是不同判断。需要先找出当前限制落在常驻载荷、临时工作区、内存 IO、计算、排队，还是模型质量，再比较合法方案。

用户给的四层能力用于备课压力测试；第一、二层已有较强表现是用户提供的背景，不能由本次研究重新认证。第三层应让多项选择的乘积、抵消、前提冲突和瓶颈转移可见；第四层应留下约束发现、证据选择、候选构造、试验解释和修订工作的空间。专业上没有“把所有优化打开”的通用最优答案。

## 2. Attention 到 cache 的必要连接

对某层某 query head，采用加性 mask：

\[
o_t=\operatorname{softmax}(q_tK_{1:t}^{\mathsf T}/\sqrt d+m_t)V_{1:t}.
\]

合法位置 mask 为 0，非法位置为负无穷。K 决定 query 与位置的匹配分数，softmax 把所有合法分数联合归一化，V 是被加权聚合的内容。换一个 query，即使 K/V 完全不变，也需要重新计算分数、归一化和加权聚合；cache 不保存一个可直接用于所有新 query 的最终 attention 答案。[Attention Is All You Need，§3.1、§3.2.1–3.2.3](https://arxiv.org/html/1706.03762)

cache 合法性的中间理由可以按层归纳，而不只用“过去算过了”：输入 token 和其位置不变；因果 mask 禁止较早位置读取未来；前一层较早位置的表示不因后缀增长而改变；本层 positionwise 投影及其合法前缀聚合于是也不改变。故较早 K/V 可以逐层复用。每一步仅为当前 token 在每层计算新 q/k/v，并追加 k/v；从当前输出预测下一个 token。以上是本研究根据因果结构作出的推导。

这份等价论证要求同一模型参数/适配器、相同 token 前缀、同一位置映射和 mask 语义、兼容的缓存数值与布局，以及固定的确定性推理规则。修改前缀中一个 token 可能影响其后全部位置的隐藏状态；相同后半段文字不保证相同 K/V。双向 encoder 追加内容时，过去表示可能读取新增内容，此论证不能直接照搬。固定 encoder 输出的 cross-attention K/V 则是另一种可缓存对象。cache 等价是数学函数层面的判断，浮点内核重排不保证 bitwise identical。[Hugging Face How caching works，Attention matrices / Cache class / Cache storage implementation](https://huggingface.co/docs/transformers/main/cache_explanation)

Prefill 对已知 prompt 并行求各层表示和 KV；decode 通常每请求处理一个新 token，读取已有 KV。KV cache 避免重跑历史前缀，不取消读取历史 KV。完整 dense prefill 的 attention 算术随 T 平方增长；一新 token 的 attention 算术随 T 线性增长。这里指 attention 部分与通常的完整前缀重算基线，不把所有模型计算合并成一个复杂度。[KIVI，§2](https://arxiv.org/html/2402.02750)

本研究据式直接推导：处理 G 个新 token 的 attention 工作仍含 \(\sum_{j=1}^{G}(P+j)\)，所以“每步线性”不能写成“整段生成恒定成本”。输出更长时常驻 KV、读取量和服务占用时长共同增长。

## 3. 载荷模型与可靠数量锚点

在所有 L 层均保留完整上下文、同一 K/V head 数 Hkv、同一 head 维度 d、每元素 s 字节、每请求长度 T、B 条互不共享缓存的请求下：

\[
M_{\rm KV,payload}=2LBTH_{kv}ds.
\]

2 代表 K 和 V。这是按张量元素数的独立计数推导，单位为 byte；它不含权重、临时激活/工作区、allocator/page padding、量化 scale/zero-point、残余高精度区、其他元数据，也不自动给出每卡峰值。GB 与 GiB 必须分清。不同层有不同窗口/头数/精度时逐层求和；不同请求长度时逐请求求和；共享时按实际唯一物理载荷计数。

自拟、可手算的示范模型：L=32，Hq=32，Hkv=8，d=128，s=2 byte，T=32768，B=4。每 token 跨全层 KV 载荷 = 131072 byte = 128 KiB；每请求 4 GiB；四请求 16 GiB。保持其他条件而用 Hkv=32 的合法 MHA checkpoint，每请求为 16 GiB。若每元素载荷降至 1 byte，四请求 KV 载荷为 8 GiB，仍需另计额外开销。

以上比较只是数量关系，不是同一 checkpoint 可随意减头数的说明，也不是性能实测。GQA 按组共享 K/V，减少独立 KV heads；Hq 仍可保持 32。理论载荷小四倍不表示 query-head attention 算术小四倍，更不表示端到端速度快四倍。[GQA，§2.1–2.2；§3.1、Limitations](https://arxiv.org/html/2305.13245)

## 4. 选择的身份、作用与失效边界

| 选择 | 改变什么、为什么可用 | 关键前提或代价 |
|---|---|---|
| 完整精度 KV cache | 复用因果前缀各层 K/V，避免历史前缀重复计算 | 前缀及模型/位置/mask 兼容；常驻载荷仍随长度增长 |
| GQA/MQA checkpoint | 多个 query heads 共享较少 K/V heads，减载荷及理想读取量 | 模型结构/权重选择；转换原 checkpoint 通常需适配训练和质量检查，不能视为无损运行时开关 |
| FlashAttention | 分块、在线 softmax 统计与正确归一化合并，使完整 attention 不必把 T×T 中间矩阵写入 HBM | 保持完整 attention 数学运算，仍有 dense 算术、KV 输入；所用 backend/精度/硬件须核实 |
| PagedAttention | 逻辑块映射物理块，按需分配并可共享，减少预留与碎片浪费 | 不改变每个唯一 token 的 KV 信息量；有块尾浪费、索引和内核开销 |
| KV 量化 | 降低载荷字节，可能降低读取带宽压力并提高可容纳并发 | 数值近似、尺度/残余区及去量化成本；不同模型/任务/内核有不同收益 |
| 原生 SWA 与 rolling cache | 每层只读取合法窗口，淘汰已不再需要的层内 KV | 与原生 SWA 的函数可等价；把 full attention 改成窗口是改变模型可见信息 |
| Prefix reuse | 相同完整前缀可共享已计算 KV 并跳过其 prefill | 精确 token 及影响表示的配置兼容；相似语义不够；decode 仍读取合法 KV |
| RoPE/位置扩展 | 改变位置表示映射以支持更长范围，常配模型适配训练 | 长度配置不证明质量；旧 cache 不可在未经兼容处理时直接接新映射 |
| 限制并发/请求长度、offload、检索或摘要 | 改工作负载、资源位置或输入内容 | 改变排队/IO/任务证据；不是免费等价，需围绕用途检验 |

FlashAttention 的在线合并必要连接：各块独立 softmax 后直接相加是错的，因为分母不同；需要保留各块最大值和指数和，并缩放到共同最大值后合并。这样可得到全局归一化结果，而无需常驻完整分数矩阵。它所省的中间矩阵和 KV cache 所存的 K/V 是不同对象。[FlashAttention，§3.1、Algorithm 1、Theorem 1](https://arxiv.org/html/2205.14135)

PagedAttention 使地址不连续不等于 attention 可见位置减少。逻辑块表维持 token 顺序与对应 K/V；内核按表读取。大块可增加处理并行性，也会增加块尾碎片，所以块大小有权衡；分配收益能让更多请求同时驻留，但这种更高并发本身会重分资源。[PagedAttention，§4.2–4.3、§7.2](https://arxiv.org/html/2309.06180)

KIVI 的代表机制是 K 按 channel、V 按 token 采用不同量化分组，另保留近期/不完整组的高精度 residual；其实现把去量化与矩阵乘融合。因此 bit 数只估主载荷，不能把峰值总显存按位宽直接同比缩小。论文结果是指定模型/任务/硬件下的经验，不能许诺任意量化无损。[KIVI，§3.2–3.3、§4.2.3–4.2.4、Appendix D](https://arxiv.org/html/2402.02750)

原生滑窗的 rolling cache 只保存每层后续确实会读取的位置；Mistral 原论文给出层间间接传播可越过单层窗口的解释。这不等于模型能直接访问任意远处原 token，也不证明“层数×窗口”范围内事实可可靠找回。[Mistral 7B，§2](https://arxiv.org/html/2310.06825)

## 5. 联动：不能只给各技术的独立优缺点

以下是根据以上机制与计数得到的研究判断候选，供 SK03 选择实际认知操作。

1. **模型头数 × 精度 × 有效驻留长度 × 并发**：理想载荷是乘积。减头或量化释放的空间若全部用于增加 B，峰值 KV 可能回到原数，且每轮 aggregate IO 增加；没有自动的单请求延迟承诺。
2. **FlashAttention × KV cache**：前者处理 score/softmax 的 IO 和中间存储，后者处理跨步重复。组合可行，但减少 prefill 中间量不保证解决 decode 的长 KV 读取；两者不同基线的 speedup 不能相乘。
3. **Paging × prefix sharing**：paging 提供可共享块和按需管理的结构；是否有相同前缀决定实际共享收益。四请求都长但内容不同，不会因分页自动减成一份 KV。
4. **Prefix reuse × 新 token decode**：命中减少共享部分 prefill；每个新 query 仍需与其合法前缀比较。若输出很长而 prefix 很短，APC 可能只改善较小部分。[vLLM APC，Introduction、Limits](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)
5. **Prefix reuse × 前缀改写/位置/适配器**：相同 suffix 不够，earlier prefix 参与后层表示。vLLM 的块 hash 包含 parent hash、精确 tokens、LoRA/多模态等额外身份信息。改动配置时须按具体 engine 重新核 cache 兼容，不能用文字相似度判定。[vLLM Prefix Caching design，hash components](https://docs.vllm.ai/en/latest/design/prefix_caching/)
6. **窗口 × 分页/共享**：原生窗口限制可驻留/可读取的对象，paging 控制它们的地址和分配。哪一层仍有全局 attention、engine 如何共享已过窗口块，决定总量；不能把全部层统一替换成 W。
7. **量化 × kernel**：量化可能省存储但多出去量化/精度转换；支持矩阵须具体核。当前 vLLM 官方文档把 per-head scaling 与 Flash backend/校准关联，并允许个别层保持原精度。此时“全模型一个 s”会错；某些 FP8 backend 连 Q 也量化，不能仍称原全精度函数等价。[vLLM Quantized KV Cache，Overview、Supported schemes、Skipping Specific Layers](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/)
8. **位置扩展 × cache/质量**：增加可计算位置不产生远证据任务能力；PI 使用位置插值配适配训练，所给结果支持该实验配置，不能证明所有 RoPE scaling 都有相同效果。[Position Interpolation，§2.1–2.3、§3](https://arxiv.org/html/2306.15595)

两条有区分力的边界：若系统已紧密分配且唯一 KV 载荷 16 GiB 而仅有 10 GiB 可用，分页和 FlashAttention 不会把该载荷压到 10 GiB；若原系统为每请求预留很大的最大长度但实际很短，paging 的分配收益则可能决定可行性。若任务只需近期信息，原生窗口可能满足用途；若需任意远处的精确证据，窗口方案需要新增检验，不能只用显存数字作取舍。

## 6. 未知约束、竞争目标与证据不足时怎样决定

完整决策应有如下接口，既不提前固定“量化最好”，也不以信息不足为由停止工作：

- 建立用途指标及硬约束：准确性/证据引用要求、输入/输出分布、到达率与峰值并发、TTFT、逐 token 延迟或 TPOT、端到端尾延迟、吞吐、预算。平均吞吐高不保证 p95 延迟低。
- 标记已知/未知：模型结构及训练长度、实际剩余 KV pool、层类型、prefix hit rate、可接受质量下降、backend 支持和硬件条件。只请求能改变方案的缺项。
- 先用计数排不可能候选：唯一载荷下界超容量时，省 allocator 不能解决；需要减 B/T/s、换合法 checkpoint、offload/更多资源或改变任务输入。
- 把瓶颈假设写成可反驳主张：例如“TTFT 被重复 prefill 主导”，其检验是同前缀 warm/cold 配对；“decode 被 KV IO 主导”，其检验需固定模型/工作负载，比较长度、batch、精度及 profiler 行为，不能从显存大直接推定。
- 设计最低有区分力的测量：代表性 input/output lengths；cold/warm prefix；峰值显存含工作区；p50/p95 TTFT/TPOT；固定到达模式；精度对照及远证据任务。每次明确保持/改变了什么。
- 保留可接受多解：若先保障质量可降并发/准入、若硬吞吐高可测量量化+共享、若允许模型替换可选经任务验证的 GQA/长上下文模型。无需假装有唯一排名。
- 明确停止/修订条件：不满足硬约束则拒用；质量不降但 latency 未改善则保留容量收益、撤回速度主张；warm 只改善 TTFT 则把下一步指向 decode/排队；新 evidence 应改结论、约束或试验，而不只是追加技术名词。

这一接口是基于机制的决策方法设计，不是已执行生产优化或已验证最优性。任何自拟性能表必须标“教学设定的观测”，不能冒充论文或设备实测。实验必须说明同 checkpoint 还是跨模型，冷启动/缓存命中是否相同，单请求/并发是否相同，以及质量门槛何时确定。

长上下文质量至少分长度、证据位置、数量/跨段连接、干扰强度和任务类型。RULER 的多针检索、多跳追踪、聚合等任务说明单针找回只覆盖有限行为；其 synthetic 性质也限制外推。Lost in the Middle 的位置对照说明读取相同数量 token 仍可能因证据位置而变质，结果来自论文所测历史模型，不是现有所有模型的定律。[RULER，§3、§8](https://arxiv.org/html/2404.06654)、[Lost in the Middle，§2–4](https://arxiv.org/html/2307.03172)

## 7. 交教学方的输入/支持/教师锚点

**可见输入候选**：第 2 节公式、逐层因果解释、prefill→decode 的同一 token 轨迹；第 3 节计数示范；第 4 节明确方案身份；第 5 节按实际取舍挑一至两条联动连贯展开；第 6 节把同一部署提案推进到可检验方案。教师先示范哪些连接由 SK03 决定，本文不把所有研究候选变成必做问题。

**备用帮助候选**：若混淆 Q 与 K/V，提供两个 query 共享同一 K/V 但产生不同权重的最小算例；若 memory 计数卡住，先画 layer×KV heads×positions×K/V 两份张量而不直接替学习者选路线；若联动失去主线，返回同一个方案表的“函数、载荷、IO、质量、指标、证据”接口。提供帮助会代做相应识别/连接，后续自主性判断需按实际暴露限定。

**教师核验锚点**：接住正确的“信息不足”和多个满足条件的方案；拒绝以 GQA 头数当任意运行时开关、以 FlashAttention 消除 KV、以 paging 压缩唯一 token、以窗口/RoPE 配置保证远证据推理、以 NIAH 保证综合推理、以吞吐代替尾延迟。观察决策层需看学习者是否主动界定可行性、优先级、未知证据及修订规则；教师已给的排名、试验清单或失效点不能再作为学习者独立发现证据。

## 8. 实际读取、版本与未核范围

已读共享原始规则：AG2-materials.md（2026-10-11修订）、learning-materials/SKILL.md、domain-checks.md、materials-workflow.md 的当前研究/读取/准备/核验部分、disciplinary-to-teaching.md。仅这些共享规则，不读取本主题历史产物。

外部实际浏览均为原论文 arXiv HTML 或项目官方文档；2026-10-11 访问。实际精读范围：

| 来源 | 实际范围/定位 | 用途与未核 |
|---|---|---|
| Attention Is All You Need | §3.1、§3.2.1–3.2.3，公式(1)、mask 为负无穷说明 | attention/因果结构；未全面审阅训练/实验 |
| HF How caching works，main | Attention matrices、Cache class、Cache storage implementation | cache接口/存储与mask连接；未执行示例，main 不视为固定安装版本 |
| GQA，arXiv v3 2023-12-23 | §2、§3.1–3.3、Limitations | 结构/转换/实验条件；图只读 caption 和正文，未检图像细节 |
| FlashAttention | §3.1–3.2，Algorithm 1/Theorem 1，相关 proof 片段 | tiling/归一化/复杂度；未完整复核 appendix proof、GPU实现或全实验 |
| PagedAttention | §4.2–4.3、§7.2，block table/粒度与kernel开销 | 分配/共享机制；未执行 vLLM、未核全部调度器/多卡代码 |
| KIVI，arXiv v2 2024-07-25 | §2、§3.2–3.3、§4.2.3–4.2.4、Appendix B/D 相关片段 | 量化机制/分组/残余区/实验边界；未复现内核和基准 |
| Mistral 7B | §2，Table 1，rolling buffer/chunking正文与caption | 原生SWA及层间传播；未读模型权重、未判泛化到其他模型 |
| Position Interpolation | 摘要、§2.1–2.3及实验说明相关片段 | RoPE位置映射/适配；未核全部理论界证明/最新变体 |
| vLLM official latest | APC Introduction/Limits、Prefix Caching hash/operations、Quantized KV Cache Overview/schemes/calibration/skip layers | 当前支持有版本和backend条件；未锁安装commit或跑示例，不能保证任何环境兼容 |
| RULER，arXiv v3 2024-08-06 | 摘要、§3任务定义、多跳片段、§8限制正文 | 质量评测维度；未重算图表/复现任务，synthetic不替真实用途 |
| Lost in the Middle | 摘要、§2–4相关位置/任务条件正文 | 位置×任务质量；未复现模型/API或重算图表 |

这些来源未给现时所有模型的性能排名。本研究没有读取图片像素、没有 GPU 性能测量、没有实际软件集成或独立实现测试；仅以可定位正文、公式、表格文字、caption 和明确推导支撑当前有限备课。HF 页 mask 的压缩写法未直接复制为数学定义，本文采用原始 attention 论文的加性负无穷 mask。KIVI 背景对模型结构作简化，本研究的 Hkv 计数以明确的 GQA 结构/具体配置为准。

研究充分范围：可支持完整机制解释、载荷推导、合法路线比较、多选择联动及有证据边界的开放决策设计。未知范围：真实学习者的操作表现、生产瓶颈、具体 engine 组合的测量结果。下一责任：主入口 SK03 把采用内容落实成实际完整备课；AG3 从原用途检查并可把具体疑点回问。本文不宣布实际学习效果或单元通过。

## 9. 主入口拟用共享算例的回问核验

主入口提供同一 GQA 服务算例后，本角色独立按唯一载荷计数复核：共享精确 prefix 长 P，B 条请求各自达到 T 的驻留上界，独有 suffix 长 T−P，则唯一 token 槽位为 \(P+B(T-P)\)。这个式子要求所有层都能合法共享该 P 的物理 KV，精度配置和影响表示的条件相同；块尾/元数据等另计。

- 教师例：P=8192，T=32768，B=4，唯一槽位106496，BF16载荷13 GiB；B=8时唯一槽位204800，BF16载荷25 GiB，FP8理想载荷12.5 GiB。
- 决策例：P=49152，T=65536，B=8，唯一槽位180224，BF16载荷22 GiB，FP8理想载荷11 GiB。若题设额外开销分别为1/2 GiB，则总量23/13 GiB；在22 GiB预算下前者不满足，后者只在容量维度可行。无共享的FP8载荷32 GiB，仍超过预算。

所有数值是自拟教材条件的计数，不是GPU实测。P=49152在各请求prompt61440的范围内合法，之后每请求含独有prompt12288和output上界4096。T=prompt+output宜明示为准入/缓存槽位安全上界：最后一个采样token未必继续被处理入cache，教学计数不应把预测token与已处理token混淆。共享不能把各query与历史合法K/V的逻辑attention工作除以B；实际硬件可能有读复用，但收益需测量。还需题设确认固定checkpoint/engine可执行65536及位置映射兼容，训练长度/远证据任务质量可以保持未知留待验收；未经验证的“改RoPE即可”不补足该前提。

主入口已收到这些核验和边界，本文没有修改其拥有的文件。
