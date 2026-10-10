# 来源、实际读取与核验登记

日期：2026-10-11；版本 r1。用途：本次备课的学科依据。未读取仓库里其他测试记录／备课成品／学习会话；指定研究报告正文提到的旧案例只作为报告论述读到，没有跟随它们的链接读取。未改共享框架或真实学习 state。

## 本地原件

| 原件 | 实际取得 | 对本分析的作用与边界 |
|---|---|---|
| [研究报告.md](E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/研究报告.md) | 全文；初次命令输出被截断，随后读取中段与 RSSM 示例缺段补齐 | 学科实质研究、教学重构、代表任务与整体互校、三类未知；报告是研究建议，非已执行的新框架规则 |
| [单元学科分析工作底稿.md](E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/单元学科分析工作底稿.md) | 全文 | 以实际任务求解关系／理由，明示来源与条件，向下游交实质内容而不是策略名 |
| E:/文献资料/学习系统架构设计/personal-learning-suite/src/agents/AG2-materials.md | 全文，确认2026-10-10修订 | 材料主线可用、范围核验、三类呈现功能与真实记录边界 |
| 同套件 src/skills/learning-materials/SKILL.md | 全文 | SK02 材料模式与生成／核验／交接职责 |
| 同套件 references/materials-workflow.md | 全文分块；读取入口段补足被合并输出截断的内容 | 来源读取、六种采用结果、形式功能、内容和用途分别核 |
| 同套件 references/domain-checks.md | 全文 | 数学例与 AI 主张的证据、功能、简化及帮助边界 |
| 同套件 references/materials-examples.md | 全文 | 首次实例化时如何完整示范、保留判断和教师参考；未取其中虚构开发数据作真实记录 |

委派文本中的 shared/personal-learning-suite 路径不存在；实际规则根为上述 personal-learning-suite。曾失败的路径读取未被写为成功。框架总体接入／指纹由根 Agent 负责，本登记不冒称另一次全框架审查。

## 原始研究：实际读到哪里

### S1 — Value Equivalence

Christopher Grimm, André Barreto, Satinder Singh, David Silver (2020). *The Value Equivalence Principle for Model-Based Reinforcement Learning*. NeurIPS 2020；本次取得 arXiv v1 PDF。

[论文 PDF](https://arxiv.org/pdf/2011.03506)，[书目信息](https://arxiv.org/abs/2011.03506)。实读：摘要、§1–3、§4 与 §4.1，§5 研究协议及主要结果文字；特别读取 Definition 1、Property 3、Proposition 4 的条件。PDF 提取共28页；没有完整阅读附录证明、所有实验细节或对所有图做视觉核验。主线只使用正式定义、集合约束与论文所述方法关系；本文 lift 与数值证明是本次独立推导。

支持：受限策略／函数集合的 Bellman 更新等价；扩展集合加强约束；规划迭代所需函数范围须考虑。不能支持：任意训练 latent 自动满足条件、所有新任务保持、仅同最优动作就叫价值等价。论文模型在同状态空间定义，01 文件已单独说明 latent bridge。

另一个 NeurIPS URL 访问失败，未据其正文作主张；成功来源为 arXiv。

### S2 — MuZero

Julian Schrittwieser et al. (2020；预印本2019). *Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model*. 本次取得 arXiv v2（PDF页首2020-02-21）。

[论文 PDF](https://arxiv.org/pdf/1911.08265)，[书目](https://arxiv.org/abs/1911.08265)。实读：摘要，§1–3 主文与训练式，Figure 1 的完整文字说明，§4 开头的任务与训练／搜索预算文字。未完整读 Methods、全部附录或 visually 验图。作者个人网站 PDF 打开失败，随后使用 arXiv 正文成功。

支持：表示／潜在动力学／预测的接口；奖励、价值、搜索策略训练；不要求重建观测；原文确定性 latent dynamics；使用 MCTS。不能支持：所有环境 Markov 充分、随机风险分布已准确、经验结果与形式价值等价完全同义。01 只作有限方法摘要，不复写正文或长引文。

### S3 — TD-MPC

Nicklas Hansen, Xiaolong Wang, Hao Su (2022). *Temporal Difference Learning for Model Predictive Control*. ICML，PMLR 162:8387–8406。

[正式出版社页面](https://proceedings.mlr.press/v162/hansen22a.html)，[arXiv书目](https://arxiv.org/abs/2203.04955)。**实读范围：正式页面摘要和书目信息。**出版社 PDF 工具访问失败；arXiv PDF 因超出工具大小限制未取得；NSF镜像失败。未声称阅读全文、loss公式核验或实验详细比较。

采用范围仅为：短视界 task-oriented latent trajectory optimization 与 learned terminal value 联合使用的原始设计目的。更详细规划／训练接口由 S4 的实际章节支撑；01 两阶段数值例是本次自拟，非 S3 的实验。

### S4 — TD-MPC2

Nicklas Hansen, Hao Su, Xiaolong Wang (2024；预印本2023). *TD-MPC2: Scalable, Robust World Models for Continuous Control*. 本次使用 arXiv v2 HTML（2024-03-21）。

[原论文 HTML](https://arxiv.org/html/2310.16828v2)，[书目](https://arxiv.org/abs/2310.16828)。实读：摘要、§1–2，§3.1–3.3；Eq.(2)、(3)、(6) 的可读公式与相关解释；§4 的任务／基线／数据设置文字及§4.1开头。未完整读 Appendix、所有 ablation、所有 figure 的视觉内容，未重现代码或训练结果。

支持：五组件接口、joint embedding／reward／TD value objectives、decoder-free 与 latent prediction 并存、MPPI 式 trajectory sampling、terminal bootstrap、首动作执行与重规划、task embedding。不能支持：单独有 task embedding 就恢复编码丢失的当前状态，或这套训练在新部署已充分。01没有以论文 aggregate benchmark 结论给本地模型打分。

## 本次独立推导、数据与执行

1. 102维观测 MSE、位置／奖励／行动排序反例：01 §3.1–3.2；自拟代理观测与精确数值，不是图片基准实测。
2. 奖励切换后的同编码冲突：01 §3.3；输入相同性论证支持给定编码的表达不可能，枚举支持该有限域的完整核查。
3. 同状态 lift 的受限价值等价：01 §3.4；由 Bellman 定义直接证明，增加 \(v_c=c\) 的差为0.9。
4. 固定候选集下 \(\Delta>2\epsilon\) 与 regret≤2ε：01 §2.3；直接不等式推导，不以观测 MSE 推 ε。
5. 扩动作 J、两阶段维护、位置历史、随机终点与尾事件：01 §4–5；完整规格与手工参考，不冒称真实环境数据。
6. 根 Agent 已执行 [verify_examples.py](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/code/decision-sufficient/preparation-r1/verify_examples.py)，通过父子消息返回全域 r0/r1 aliasing、MSE与真实回报核验；是备课检查，不是学习事件，也不证明神经训练可得。其余独立推导明确在01，未虚称已在脚本运行全部变式。
7. 认知 Agent 回问定位到 T2 的专业输入缺口后，学科 Agent 在01 §2.4补有限离散期望定义与独立线性收益示范：Y取2(0.25)、6(0.75)，g(y)=3y+1，E[Y]=5，E[g(Y)]=16。算术与仿射期望性质由展示步骤直接核验；未拿 T2 的平方目标教完，也未新增真实学习事件。这是本次实际发生的学科—认知往返。

检索停止理由：当前用途所需形式定义、真实方法接口与合法玩具推导已具备。无需为本次继续扩展全部 world-model 论文；尚未取得的实验／新部署性质保持未知，待具体需要才回查。

阶段二根 Agent 后续核验：同一规范脚本实际加入 T2–T4、独立线性期望示范、位置历史及 VE 闭合性的具体见证并重跑通过；范围与最终代码指纹见 [数值核验](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/experiments/decision-sufficient/preparation-r1/numerical-verification.md>)。初次委派消息中的有限运行范围是当时事实，后续运行不冒充此前已经完成，也不覆盖尾风险或 T5 未知部署。
