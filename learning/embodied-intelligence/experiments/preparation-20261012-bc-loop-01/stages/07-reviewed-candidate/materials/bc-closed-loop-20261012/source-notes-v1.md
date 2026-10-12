# BC 闭环专业来源与执行读取回执 v1

对象 `EMB-BC-CLOSED-LOOP-SOURCES-20261012`，revision 1，owner AG2，`pl-contracts/0.1.0` 人工 SourceFragment 视图。访问日期 2026-10-12；具体访问时刻未记录。用于 `disciplinary-research-v1.md` revision 1 的有限专业研究，不表示全部来源全文精读或全部模态核验。

## S1：DAgger 原始论文

- 来源身份：Ross, Gordon, Bagnell，*A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning*，AISTATS 2011，PMLR 15:627–635。固定出版稿，[原始 PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf)。非本套件 D/R/N 资源编号；本稿来源 ID S1。
- 已读文字 known：PDF第1–4页的 introduction、§2、§2.1/2.2、§3、Algorithm 3.1 和 §3 定理前提。网页抽取定位主要是行35–418。相应上下文含输入分布由策略诱导、专家标注、混合采样以及保证所需假设。
- 已读公式 known：§2 的 d_π、J、代理损失，Eq(1)/(2)，Theorem 2.1/2.2 和 3.1/3.2 的抽取公式及解释。数学表达由文字抽取读取，未取得公式图像，不声称视觉排版核验。
- 图像 unknown：尝试 PDF 页截图，宿主只回来源定位字符串，未返回可观看图像；所以未核图像、图/表及公式版面。
- 已核主张 supported（内容修订1）：专家输入分布与自身输入分布有区别；DAgger 的访问状态由专家给动作标签并聚合；T²ε 及 uTε 主张仅在文中指定损失、代价/恢复条件下使用。本稿不将连续 MSE 代入这个保证。
- 方法 source_comparison；required_modalities 为 text/formula；锚点 §2.1 Theorem 2.1、§2.2 Theorem 2.2、§3 Algorithm 3.1/Theorem 3.1–3.2。
- 未读/未核 known：有限样本证明、§4 完整证明、§5 实验全部细节与图表、附录；未复现。来源核验只覆盖上列主张，不为任一真实机械臂提供自动保证。

## S2：robomimic 人类示范研究

- 来源身份：Mandlekar et al.，*What Matters in Learning from Offline Human Demonstrations for Robot Manipulation*，CoRL 2021；PMLR出版于2022，164:1678–1690，[固定出版稿 PDF](https://proceedings.mlr.press/v164/mandlekar22a/mandlekar22a.pdf)，[出版记录](https://proceedings.mlr.press/v164/mandlekar22a.html)。来源 ID S2。
- 已读文字 known：PDF第1–5页 introduction、§2五类挑战、§3任务/数据/评价协议、§4.1，以及第7–8页 §4.5–4.7、§5；并读网页抽取中相应表题说明。主要抽取行25–212、306–368。
- 已读公式 not_required：当前使用范围是实验设计及条件化结论，不依赖未读公式。
- 图像 unknown：页截图尝试无可见图像；未视觉核验 Fig 5 的曲线/柱状值；因此研究稿不复用其数值图、百分比和全部排序。
- 已核主张 supported（内容修订1）：论文在其任务上比较历史依赖和观察选择；§4.5明确最低验证损失/最后 checkpoint 与最佳闭环性能选择可能不同。主张限定为这项研究，不将架构消融倒推真实项目唯一因果。
- 方法 source_comparison；required_modalities 为 text；锚点 §2 C1/C4、§3.3、§4.1、§4.5、§5 L1/L3/L4。
- 未读/未核 known：全部观察空间/超参消融细节、全表数值和原始代码/数据、附录与补充材料。本次 arXiv PDF / 项目网页访问失败，未把失败访问记为已读；使用可读 PMLR 原稿作为独立可定位原件。

## S3：ACT 原始论文

- 来源身份：Zhao, Kumar, Levine, Finn，*Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware*，[arXiv 2304.13705v1](https://arxiv.org/abs/2304.13705v1)，2023-04-23，[v1 PDF](https://arxiv.org/pdf/2304.13705v1)。元数据页显示该论文只有 v1；实际读取未带版本 URL 的 PDF，身份已通过元数据核对应 v1。来源 ID S3。
- 已读文字 known：PDF第4–5页 §IV/IV-A/IV-B 的对象和执行机制；第9–10页 §VI-A 和附近失败/限制段。主要抽取行372–503、769–849、938–949。读低层 target joint position 标签说明以避免混淆动作定义。
- 已读公式 known：Algorithm 2 推理 buffers 对同一执行时刻的预测做加权平均，及正文 wi=exp(-m i) 和索引含义；使用“同刻融合”而不复用具体权重实现。训练 Algorithm 1 虽见抽取，不作为本次训练损失/实现保证。
- 图像 unknown：截图工具没有返回可见图像，未核 Fig4/5/8 成品。抽取图注已读属于 text，不冒称图已看清。
- 已核主张 supported（内容修订1）：块长度与重查频率有区别；集成对同一目标时刻的重叠预测；原文消融不支持无限加长或所有算法都因融合改善。方法 source_comparison；required_modalities text/formula；锚点 §IV-A、Algorithm 2、§VI-A。
- 未读/未核 known：网络架构全细节、硬件搭建、全部实验图/表与附录、代码版本/运行；未核总体效果百分比。来源只能支撑本次结构取舍，不能保证某真实任务的选择。

## S4：Diffusion Policy 原始 RSS 版本

- 来源身份：Chi et al.，*Diffusion Policy: Visuomotor Policy Learning via Action Diffusion*，[arXiv 2303.04137v3 PDF](https://arxiv.org/pdf/2303.04137v3)，v3 于2023-05-22；使用原2023稿，未使用扩展2024 v5的实验结果。版本元数据由[arXiv来源页](https://arxiv.org/abs/2303.04137)核得。来源 ID S4。
- 已读文字 known：introduction 的任务表征问题；PDF第3页 §III-C动作序列和三个时域，第4–5页 §IV-A/C 的多模态/时间一致性说明，第11页 §VIII限制。主要抽取行41–67、260–280、406–436、477–484、1029–1043。
- 已读公式 known：条件 p(A_t|O_t) 及 T_o/T_p/T_a 的含义；扩散/score 的训练与采样公式未精读，不用作该算法完整教学依据。
- 图像 unknown：截图尝试无可见图；未核 Fig3/4的可见成品，抽取图注不等图像阅读。故未复制图及其有限 rollout 图证据。
- 已核主张 supported（内容修订1）：预测时域与执行时域不同；多模态/段内一致性是论文结构动机；论文明确示范不足与推理延迟限制。方法 source_comparison；required_modalities text/formula；锚点 §III-C、§IV-A/C、§VIII。
- 未读/未核 known：完整扩散模型推导、全部基准数值、实时代码与附录/视频、当前库接口，未复现。初次尝试官方名称猜测 PDF 路径失败；未将其列为已读来源。

## 原创推导与教学情境

研究稿 §3.1（同环境同误差、不同反馈）、§4.1（非凸合法动作集合与均值）和 §4.2（延迟改变特征根）是 AG2 按明确假设独立推导的局部材料，不是论文原例或真实实验数据。核验方法 derivation，锚点为同稿完整定义/推导/分支；required_modalities text/formula。所有表数值可由递推与闭式读回核验，未运行仿真、未制作图像或媒体。机械臂阶段及实验提案是条件化专业分析候选，没有学习者表现、真实项目日志或已执行实验身份。

## 实际规则读取与未读取范围

本执行实际取得：

1. 学习目录 AGENTS.md、MODEL_ENTRY.md、FRAMEWORK.md 全文；state/control.md 当前头部 revision11、state/current.md 当前头部 revision22，以及保存的 learning-request.txt。早期一次批量工具调用还输出了 state 旧历史条目的可见片段；其未用作本次学科依据或个体判断，不声称完全未访问历史状态。
2. `../../personal-learning-suite/src/agents/AG2-materials.md` 当前2026-10-11指导全文。
3. `../../personal-learning-suite/contracts/shared-contracts.md` 全文，版本 pl-contracts/0.1.0。
4. `../../personal-learning-suite/src/skills/learning-materials/SKILL.md`，`references/domain-checks.md` 和 `references/materials-workflow.md` 全文。
5. `../../personal-learning-suite/src/skills/learning-teaching/references/disciplinary-to-teaching.md` 全文。

有一次批量返回被截断；上述必要专业规则随后单独取回，未以被截断结果当全文已读。当前只是学科研究环节，尚未读取 AG1 认知稿、design-whole/Encoding/Post/SK06包或材料实例，不把认知设计与成品核验记为已完成。SK00/AG0 主入口由父入口负责，本执行未声称兼任或完成其读取。

没有读取旧“教学转换/学习深度损失/Agent质量”专题审计报告及诊断，也没有沿规则末尾历史链接加载审计/研究/实施报告；没有读取 `experiments/preparation-20261012-bc-loop-01`。未把额外归档、套件 fixtures/examples 或 synthetic数据库作为专业输入/真实记录。

检索停止依据：四份原始论文与三个可独立核的关系模型足够支持当前有限范围的专业对象、竞争解释、条件变化、改进取舍和实验依据；继续全面扩展文献不改变当前交接。当前未做真实工程诊断，不需补画像后才能设计有限纸面第一阶段。

## 当前用途与交接边界

`SourceFragment` 读取/内容核验已具上列限定范围；`MaterialUse` 的学习者可见输入、备用帮助、教师参考与实际功能须待 AG1 认知设计后落实。当前稿及来源只用于后台学科交接，prepared，不是 displayed。不会以截图尝试成功定位声称图像已读，不会以四论文相互一致证明新情境答案。

下一接收者 AG1/SK03；如返回具体缺口，AG2 只回修受影响关系与来源，并另存 v2。当前 v1 不覆盖；接受、采用与范围确认由父入口/对应专业方另记。
