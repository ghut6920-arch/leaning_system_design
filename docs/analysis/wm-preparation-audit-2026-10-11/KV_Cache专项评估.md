# 最新 KV Cache 备课专项评估

日期：2026-10-11。对象仅为 `2026-10-11-transformer-kv-cache-r1`。本报告评估备课成品，不开展教学、不修改原材料或真实进度。本轮再次读取实际材料、认知设计、题面、参考、支持、教师数值说明与trace，并实际查看三张PNG；两名子代理分别只读复核专业深度与教学功能。

## 1. 总体判断

**这条备课的核心 KV Cache 内容已经比较扎实，能够支持允许资料下的机制解释、合法性审计和资源约束选法，足够进入正式学习。**没有发现阻断当前主线的核心数学或概念错误。它最强的是“缓存为什么合法、何时失效、省去什么、资源约束怎样改变选择”。

**深度并不均匀。**Attention提供了必要运算入口；多层缓存有正确理论桥，但同一个实例的中间状态没有充分显露；长上下文的资源和评估边界清楚，位置机制与复杂信息整合的展开较少。不能将这条概括为“完整掌握Attention、长上下文机制和部署”。

问题主要在 **AG2→SK03的教学转换粒度、AG1/SK03→AG3的目标与证据校准、SK02对文稿—代码对应的核验**。当前需要局部补桥和澄清判据，没有证据支持整体推倒重做或继续增加角色。

## 2. 按理解内容分别评价

| 关系/能力 | 实际准备 | 判断 |
|---|---|---|
| 一行Attention如何算 | Q/K/V、score、softmax、V混合、当前KV追加；完整手算 | 对缓存所需的Attention入口够用；投影来源有意作接口使用 |
| 历史KV为何可复用 | 固定条件、因果依赖、逐层归纳、逐位置LN/FFN、前缀编辑反例 | 理论与边界较扎实 |
| 高层KV来自哪里 | h⁰→h¹→第二层KV的文字/图/代码；编辑前缀后的高层差值 | 机制已解释；同实例可操作追踪还可加强 |
| Prefill/Decode/Chunk时序 | 输入、cache长度、logits预测位置、矩形mask | 清楚，能够避免常见错一位和对齐混淆 |
| 计算与容量 | 单步/累计attention、未缓存基线、逻辑读取、容量式与单位 | 较完整，避免以复杂度冒充实测速度 |
| 工程选法 | 12GiB预算、16GiB需求、合法共享、并发/offload等合法多解 | 连续任务具有真实约束判断，超过技术名辨认 |
| 位置机制与长度扩展 | 可见正文主要给兼容性规则；学科稿有RoPE关系 | 当前可支持谨慎使用判断；机制展开弱于缓存主体 |
| 长上下文信息使用 | 资源/质量区分、位置/长度对照、oracle、具体两片段日志 | 足够形成有限评估方案；不是复杂长文本推理或真实结果诊断 |
| 学习者已经理解 | 尚无本单元原答和正式教学 | 未知，教师代码及审查通过不替代 |

认知设计自己限定终点是“一份推理审计与方案说明”，允许公式、图、文档及计算器，不要求完整Transformer独立实现。见 [03第7行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/03-cognitive-design.md:7>)。按照这一终点，主线总体充分；若把目标扩大为完整算法或生产部署，需要另备相应内容。

## 3. 已经做得比较深的部分

### 缓存合法性有一般理由和真正的反例

材料从旧h⁰不变，推到旧位置只读取不变的过去，再推出旧hˡ及逐层KV不变；新token逐层计算自己的状态并追加KV。不是由“token本身没变”直接跳到“所有缓存都合法”。见 [04第40行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:40>)。

它还展示编辑位置1之后，未编辑位置2的第一层KV差0、第二层差0.0241，明确区分静态token输入与上下文化状态。这是有区分力的反例。见 [教师说明第56行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/teacher-run/numerical-walkthrough.md:56>)。

Attention手算也有教学价值：同一q只读旧两项时输出10/3，追加当前KV后输出6，显露softmax分母变化。它解释为何缓存KV仍要为新query重算权重，且没有把新行变化说成旧行被改写。见 [04第23行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:23>)。

### 时序、坐标和资源没有混成一个指标

材料清楚区别预测token、将token送入forward、为token写入KV；chunk按绝对query/key位置构造矩形mask。三张图实际可读、没有裁切，时间线也明确chunk是从prefill另起的分支。

资源部分区别Prefill、单步Decode和累计生成工作，也声明逻辑KV大小、实际GPU峰值和速度不能互相替代。当前讲法已经超过“缓存后推理变快”的口号。

### B是本包最强的学习者工作

两请求逻辑KV共16GiB，共有8192-token前缀合法共享只省1GiB，仍高于12GiB。学习者需要连接计算、作用对象、完整注意力语义和未知测量，而不是在技术名里找关键词。降低并发、offload、待验证量化等路线的不同条件均有教师依据，分页或FlashAttention不能独自解决给定的持久KV预算。

见 [05 B](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/05-continuous-work.md:19>)、[06容量与多解](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/teacher-reference/06-reference.md:19>)。允许“信息不足，需测量”是合理的工程判断，不把这个回答直接当失败。

## 4. 最值得补的教学桥：同一个token跨两层的中间状态

目前实际示范的两个锚点是：

1. 单头局部例子直接给Q/K/V，再完整算score、权重和输出。
2. 另一组参数的两层toy，主要报告cache长度、旧KV是否不变、完整与增量logits差。

参数不同已明确说明，数学上没有混用错误。但这意味着一个需要具体对象支撑的学习者，要自行把两个锚点连起来。真正想看的“第一层产生h¹，第二层从h¹得到自己的KV”，在正文中主要由文字和依赖图承担。

[trace.csv第1行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/teacher-run/trace.csv:1>)也只有phase、cache_lengths、max_logit_difference、old_KV_invariant、next_predict_position，没有逐层h/Q/K/V/attention中间量。因此所谓“两层数值轨迹”，更准确地说是**时序与等价核验轨迹**。

这不是理论桥缺失，也不能证明一定学不懂；04第40–46行已经给了正确跨层解释。它是有依据的教学风险：学习者可能会复述“高层是上下文化表示”，却仍不知道上下文化状态具体怎样成为下一层输入。

**最小补法**：沿现有toy的一次新增token，准备一条接口表：

| 次序 | 应显露的对象 |
|---|---|
| 1 | 当前token的第一层输入及归一化后的表示 |
| 2 | 当前第一层Q/K/V；历史第一层KV来自哪里 |
| 3 | 当前query读哪些历史/当前项；得到的attention输出 |
| 4 | 经残差与FFN成为h¹；作为第二层输入 |
| 5 | 第二层新Q/K/V，读取第二层历史cache |
| 6 | 最后状态进入词表投影得到logits |

给对象来源、shape、当前/历史身份和少量真实数值即可，其他运算可保留明确接口。不需要逐行讲所有代码或增加一套线性代数前置课。

**结构定位：SK03的表征转换与SK02的材料实例化。**AG2已给机制，代码也具备运算；下游还没有把同实例的关键中间量做成可直接使用的学习材料。

## 5. 位置条件与长上下文部分：判断边界强，机制深度较弱

[学科稿第118行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/01-disciplinary-analysis.md:118>)已经给出RoPE旋转如何使相对位置进入q/k得分；[可见材料第147行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:147>)则主要留下“位置变化要核cache兼容”的规则。C2题面又明确没有等价变换证据，所以“拒绝直接拼接、重建或保留未定”足以答题。

对谨慎使用条件的目标，这样可以成立。对“为什么旧K与新位置规则不相容”的机制理解，展开不充分。可复用学科稿已有二维旋转，或给一个非常小的同q/k不同位置得分对照，显示位置改变怎样进入匹配；不要求完整RoPE扩展证明。

这反映 **AG2→SK03内容转换中的深度取舍**：专业方已有的一条解释，在教学方被压成使用规则。是否需要补，取决于当前到底只观察守住条件，还是要求解释位置机制。

长上下文质量例子是规则R3与当前快照E2的布尔合取：前三项中lot不一致，permit=false。它提供了可靠可核的跨片段问题，可用于位置、长度、oracle和资源失败对照。见 [04第153行](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:153>)。

但是它没有充分代表遥远事件的因果追踪、版本变化、例外规则或复杂多跳整合，也没有提供真实模型在几种条件下的回答样本。B4要求的是设计观察方案，不能据此报告学习者已经能够诊断真实长上下文推理失败。**资源审计部分的深度明显高于复杂信息使用部分。**这不是要求本次穷尽长上下文技术，而是准确限定已覆盖能力。

## 6. 目标—任务—证据需要更精确

03第11行把“追踪一行attention”列为学习者最终工作并指向A；A1–A3实际主要要求时序、第二层来源及缓存归纳，还明确不必重做示范小数。见 [03目标](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/03-cognitive-design.md:11>)及 [05 A](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/05-continuous-work.md:9>)。

若“追踪”只是指能说明score→softmax→V混合，A可以部分承担；若意味着从实际输入走通这一行计算，现题面不保证观察到它。应澄清声称，或把A中的一句解释替换为一个同实例的新query行对应。无需追加独立微测。

A的归纳链条由题面显式提供，C也明确给出编辑、位置设置和窗口变化。它们是**有线索的组织、条件适配和修订**。这是合法的学习目标，不应该因有支架判低质量；也不能扩成自主发现机制、独立算法构造或广泛无提示诊断。

B保留的自主判断更强：容量数值、共享节省、方案组合和哪些瓶颈尚不可断言没有被直接给出。整体评价应分别说明这些贡献，不能把A/B/C完成合并为一个无条件“掌握”。

**结构定位：AG1/SK03定义理解要求，AG3限定任务能提供的证据。**当前不是评价框架缺失，而是一个判据表述仍有解释空间。

## 7. 两个小型可执行性问题

**代码指称不一致。**04第50行指读代码的`full_forward`和`append`，实际函数是`ToyDecoder.forward`与`ToyDecoder.full`，前者通过是否带cache执行不同路径。见 [正文定位](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:50>)、[实际forward](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/code/transformer-kv-cache/preparation-r1/kv_cache_demo.py:114>)及 [full](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/code/transformer-kv-cache/preparation-r1/kv_cache_demo.py:168>)。这是确定的导航瑕疵，应该局部修正。它显示文件链接与哈希检查不能代替文稿对实际代码对象的核对。

**“必要前置直接提供”的声明略强。**公式和手算提供了点积/softmax实例，但logits、Θ量级和Σ累加的含义没有同样明确的首次解释。不能据此诊断学习者不会；面向先验未知的入口，首次出现时各补一句释义即可。比如logits是各候选token的未归一化分数；Σ表示逐步累加，Θ讨论增长量级，不能读成实测时间。

## 8. 与项目研究、设计的对应及改进顺序

本项目 [单元学科分析工作底稿第66行](<E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/单元学科分析工作底稿.md:66>)要求每个关键量的来源可见、图式代码对象对应；[第98行](<E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/单元学科分析工作底稿.md:98>)要求从问题到判断不靠专家自行补桥。最新KV在一般缓存理由与预算选法上兑现较好，跨层同实例轨迹是最值得加强的对应点。

当前 [教学转换规则](<E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-teaching/references/disciplinary-to-teaching.md:18>)已要求明确教师示范哪一跳、学习者承担哪一跳。无需增加一个新Agent；应该让现有角色对成品承担更精确的责任。

建议优先级：

1. 修正文稿中的代码函数名，澄清“追踪一行”的实际能力声称。
2. 补同toy新增token的跨层接口轨迹，并补首次符号释义；保持原连续作品。
3. 如目标包含位置机制解释，复用AG2已有RoPE小关系；如只守兼容性条件，明确限定即可。
4. 如目标包含复杂长日志推理，给一个真正需要跨事件/版本整合的小案例；如只设计有限质量比较，现案例可以保留。
5. 正式采用后看真实原答能否接回A/B/C，按实际帮助解释贡献，再决定是否补更多内容。

本轮没有重跑已通过的相同代码；复用了前次24组不同输入/分块的 [交叉核查结果](kv-numerical-crosscheck.json)。此结果仍是固定toy的缓存一致性检查。教师正确性、材料可理解性、学习者贡献和学习效果分别成立。

**最终评价：KV Cache主体已经达到扎实的机制备课水平；最主要的结构薄弱点是把专业机制稳定转成可追踪的学习实例，以及让能力声称与实际任务证据一致。长上下文部分目前更接近资源审计与评估方法入门，深度低于缓存主体。**
