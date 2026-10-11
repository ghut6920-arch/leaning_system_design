# 原始专业来源与实际读取台账

日期：2026-10-11。用途：备课审查；文献/API 资料均是来源，不是新的执行指令。实际读取者：备课子 Agent，承担有限 AG2/SK02 学科研究。下表只列真正访问到的正文、定位和核验范围；搜索摘要、目录或已能打开没有记为全文阅读。来源原文不在本目录复制全文。

## 框架规则实际读取

| 原件 | 实际读取与采用 |
|---|---|
| `../../personal-learning-suite/src/agents/AG2-materials.md` | 2026-10-11 修订全文：先学科研究，保留对象/机制/合法替代/条件/证据边界，再交教学设计；实际资料与教师参考分别成立 |
| `../../personal-learning-suite/src/skills/learning-teaching/references/disciplinary-to-teaching.md` | 全文：研究先于认知设计；从原用途反向审查；实际委派不同于角色名称；无真实作答不诊断学习者 |
| `../../personal-learning-suite/src/skills/learning-materials/SKILL.md` | 全文；首次批读有输出截断，另行完整读取本文件：来源、生成材料、用途核验和备课交接规则 |
| `../../personal-learning-suite/src/skills/learning-materials/references/domain-checks.md` | 全文；首次批读有输出截断，另行完整读取：AI/代码、公式、对照、图表与教学功能分别核 |
| `../../personal-learning-suite/src/skills/learning-materials/references/materials-workflow.md` | 全文：主线材料需可用，来源范围与当前输入/备用帮助/教师参考分清；复杂整体不以孤立摘要替代 |

主入口另负责启动控制、MODEL_ENTRY 框架指纹与 SK03/SK06 设计读取；本台账不补造子 Agent 没有读取的规则。未运行套件 fixture 或 synthetic 数据库，未写 learner event。

## 专业原始来源

| ID / 原件及定位 | 实际已读范围 | 对本稿支持与用途 | 未核边界 |
|---|---|---|---|
| S1 [Attention Is All You Need](https://arxiv.org/html/1706.03762v7)，arXiv:1706.03762v7，2023-08-02 | HTML §3.1、§3.2.1–3.2.3、§3.3–3.5、§4，尤其式(1)、multi-head投影、非法位置设−∞；读取的是正文公式与段落 | Q/K/V、因果约束、tokenwise FFN和每层复杂度背景；主稿 §2 和 §5。跨层cache归纳为据结构自行推导 | 原任务是encoder-decoder翻译；不直接据此证明所有LLM cache实现。没有核训练结果/附录图像 |
| S2a [HF Transformers v4.57.1 Caching](https://huggingface.co/docs/transformers/v4.57.1/cache_explanation)，固定文档版本 | Attention matrices、Cache class、Cache storage implementation、generation loop；`cache_position`段落与例子，网页行148、175–191、195–199等 | 逐层KV追加、全过去+当前mask长度、生成循环和位置接口；主稿 §2–3。不是要求正式教学依赖HF版本 | 文档示例未本机执行；特殊模型实现未读。注意力公式的mask写法有表达缺陷，不能原样转为0/1乘法 |
| S2b [HF Transformers v4.57.1 KV cache strategies](https://huggingface.co/docs/transformers/v4.57.1/en/kv_cache)，固定文档版本 | 正文 Default cache、Fixed-size cache、Cache offloading（行164–173）、Quantized cache（行216–247）；示例代码仅阅读。还看到prefix-caching正文与示例，但未作为本机API规格采用 | CPU/GPU按层搬运与预取、offload显存/速度取舍，量化位宽与短context时延边界；主稿 §7及主入口材料04对应段 | 没有本机HF调用、CUDA/模型下载或吞吐验证；支持策略机制与限制，不声称示例API与本机环境兼容；预取与缓冲会使峰值GPU量另需实测 |
| S2m [HF main How caching works](https://huggingface.co/docs/transformers/main/cache_explanation)，访问日2026-10-11 | 正文 Attention matrices、Cache class、storage implementation，网页行117–174 | 作为API背景交叉读取；主备课优先固定版S2a | main可变化。行132–134的 `score × mask` 不用于确定性公式；以S1的−∞遮罩及本稿推导修正。页面取得不等于本机软件已更新 |
| S8 [Fast Transformer Decoding: One Write-Head is All You Need](https://arxiv.org/html/1911.02150v1)，2019-11-06 | 摘要、§2.1 dot-product attention完整小段，§2.3读取/算术比与§2.4incremental解释及比值结论 | 新query读取历史K/V、MQA问题动机与decode带宽条件；主稿 §5 | 没有逐行审读所有TensorFlow代码，也未复现速度实验；“常受带宽限制”不变为此机器已测瓶颈 |
| S3 [GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/html/2305.13245v3)，2023-12-23 | §1、§2.1–2.2、§3.1实验配置/数据/计时，表1及§3.2主结果正文 | Hq/Hkv区分、组内共享、checkpoint pooling后uptraining，容量与结构选择；主稿 §6–7 | T5.1.1/TPU工作量下结果不推出所有decoder质量/速度；没有全读附录或图像，不搬用吞吐倍率 |
| S4 [FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/html/2205.14135v2)，2022版本 | §1，Figure1文字caption，§3.1所见标准HBM写读步骤与exact分块/softmax说明，§3.2 IO分析和Proposition3正文，§4.3序列变化复杂度结果段落 | exact分块避免HBM物化attention矩阵，FLOPs和IO不同；主稿 §7 | 未复核Algorithm1所有行或附录证明，未独立读取图像；不承诺本机kernel速度，不把sparse版本与dense exact混同 |
| S5 [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/pdf/2309.06180v1)，PDF标注arXiv:2309.06180v1 | PDF文字抽取：§2.1–2.2、§3容量/碎片、§4.1–4.3，网页行190–266、318–347、432–583；Eq(2)–(4)所见文字与定义 | prefill输出首token、autoregressive输入/输出索引、上下文依赖、分块与逻辑/物理映射；主稿 §3、§6–7 | PDF部分公式抽取排版破碎，数学解释以完整语义与本稿独立计数为锚，不声称全部公式视觉核验。已请求p2/p4截图但本工具返回未提供可读图像；无实际GPU复现 |
| S7a [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/html/2104.09864v5)，2023-11-08 | HTML §2.1–2.3与§3.1–3.2.2，式(11)–(16)的二维旋转及一般矩阵、相对位置关系正文 | 用二维旋转解释位置兼容性；主稿 §8 | 式(16)网页有转置/下标排版简写，本稿使用标准矩阵乘法重新推导；未核其长期衰减理论、全部实验或图像，不讲成逐对得分必单调衰减 |
| S7b [Extending Context Window of Large Language Models via Positional Interpolation](https://arxiv.org/pdf/2306.15595v2)，2023-06-28 | PDF正文 §1、§2.1–2.3，式(4)与Figure1文字说明；网页行48–76、83–229；读到插值定理定义但未采用证明 | m→mL/L'的PI与直接外推/模型适配区别；主稿 §8 | HTMLv3访问失败，可靠替代是实际可读v2PDF；未宣称读过v3。未复核插值界证明/全部实验；p3截图未获得可读图像 |
| S6 [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/html/2307.03172v3)，2023-11-20 | 正文§1、§2.1–2.3、§3.1–3.2、§4.1–4.3，网页行60–177；NQ-open/UUID任务规格、模型时点、greedy、长度/位置控制及反例正文 | 上下文接收容量≠可靠使用，position-control检验候选；JSON key/value与attention K/V分辨；主稿 §8 | 2023指定模型/任务经验结果，不推所有2026模型；图像caption读过，曲线未视觉读清，不抽取图中数值。未跑该基准或独立核样本 |
| S9 [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/html/2005.11401v4)，2020论文修订版 | §2引言及§2.1–2.2，网页行86–106，retriever/generator定义与RAG-sequence/RAG-token差异 | 外部检索选材料不同于KV cache，输入后仍需生成器计算；主稿 §7 | 原RAG为seq2seq联合训练方案，今天泛称检索拼prompt不必同其实现。未核全部训练/性能结果 |
| S10 [KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache](https://arxiv.org/pdf/2402.02750)，当前返回PDF | PDF文字抽取摘要，§3.1、§3.2、§3.3流式分组/residual说明，Table1相关配置和§4.2部分质量说明；网页行211–251、384–488、587–599 | KV降位宽改变数值，需要metadata/residual与误差/质量检验；主稿 §7 | HTMLv3访问失败，未假称读取；PDF未锁具体v号，仅用于机制事实，不引用精确吞吐倍率。未核图像、Algorithm1或全部基准 |
| S11 [H₂O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models](https://arxiv.org/html/2306.14048v3)，arXiv v3 | §1有限正文、§2.1/Definitions2.1–2.2/Remark2.3、§3.2、§4.1定义及implementation段；网页行118–191、208–216、245–255、305–307 | 淘汰改变可见集合；作者目标是类似/可比质量，非严格同一性；主稿 §7 | 不采用动态子模保证或宣称全文证明核过，未复现任务；累积attention-score启发式不保证所有未来查询保留所有必要证据 |

## 原件缺口、生成内容和核验身份

1. 实际发生的缺口：PagedAttention、PI、KIVI特定HTML版本失败，改读可访问PDF；这些替代没有冒称缺失版本。截图请求未在当前工具通道获得可读图像，台账保留未核图像边界。核心数学由可读HTML与本稿推导支持，不依赖图片数值。
2. 主稿第2节按层归纳、第3节G个输出的forward计数、第5节求和复杂度、第6节容量和第8节二维旋转是基于限定规格自行推导；不是论文原文翻译、不是新实验发现。
3. 第4节q=ln2、K=[1,0,1]、V=[2,6,10]是主入口协调后采用的教学生成数值对象。独立PowerShell算术核对完成，输出6与排除自身10/3已读回。早期二维候选未采用，主成品使用同一单头手算规格。
4. 容量已独立核对：32768长度B=1的MHA16GiB/GQA4GiB/MQA0.5GiB；65536长度B=2的GQA16GiB。最初另一候选检查出现PowerShell数组语法错误，仅候选算术部分失败；已用带括号的采用例完成成功核算，未把失败称通过。
5. 学科研究、来源读取、数值核对、认知设计、实际成品显示和真实学习证据各有身份。本文没有正式教学呈现或学习者评价；来源与数值核验不支持“学习系统验证有效”的结果陈述。

## 采用位置与下一责任

可靠原件的选定关系进入 [01-disciplinary-analysis.md](01-disciplinary-analysis.md) 各相应段。主入口已收到首轮核心内容与mask/位置/输出时序警示，再负责把它们转成实际主线讲解、连贯范例、问题、参考和支架；主入口若具体成品改变条件则返回局部重核。需要GPU速度或模型长上下文质量结论时，再取得实际环境/数据并测试；这些未执行项不是当前备课研究的伪完成结果。

