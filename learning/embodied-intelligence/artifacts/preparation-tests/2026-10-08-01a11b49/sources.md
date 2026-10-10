# 备课依据与读取范围

版本1；单模型，2026-10-08。未读取任何其他 preparation-tests 成品。目录清单偶然出现其名称，不代表读取内容；未访问另外两个对比聊天。

## 当前框架

已取得学习目录的AGENTS、control revision11、current revision22、MODEL_ENTRY、FRAMEWORK、INTERACTION。framework-manifest.json登记117项，按SHA256实际核对，差异0；这只证明登记内容一致，不证明教学收益。

实际采用的专业规则：共享契约的对象／责任与prepared/displayed、未知／未执行、原答／派生区分；SK00接入与范围、AG0；SK01/AG1近期目标；SK02/AG2及materials-workflow、domain-checks；SK03的design-whole、Encoding、Post功能与C0；SK06选法；AG3、SK04及整体作品评审。本次只准备评价依据，没有生成真实Judgment或PlanCommitment。

规则原件在 [共享框架](../../../../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md)。目标原件在 [R1—R3](../../../goals/M0-video-interface-first-20261006-02.md)。course-map和M0目录只读近期用途／M0.2，不声称重核全大纲或采用其小时安排。

## 研究与设计

直接回读：

- [Encoding研究报告](../../../../../docs/research/01_Encoding研究报告.md) §5结构属性、§9顺序、§10何时给支架：用具体对象／前后置／不变量，而非统一难度；必要术语先给；顺序按认知依赖。
- [Encoding设计D05](../../../../../docs/designs/AI个人学习系统_工作包5_Encoding_设计方案_v0.md) §二：设计单位是一组可用于判断的关系；整体义务不能由局部数量代替；内容参考、目标、诊断解释和外部支架分开。

完整策略包的两载体正文、约束与研究片段：

- [S05](../../../../../personal-learning-suite/resources/strategies/encoding/S05.json)：完整正确范例的步骤意义、观看与承担分开；OS07/08/12的外推限制保留。
- [D04](../../../../../personal-learning-suite/resources/strategies/encoding/D04.json)：正例／非例／信息不足逐条件核验；DI02/06不构成该视频任务的效果证明。
- [关系包](../../../../../personal-learning-suite/resources/strategies/post/retrieve-relation.json)：完整source_excerpts与evidence_refs；D06恢复／关系整合／最小返回，D07组合干扰／任务实例化／帮助作用，R04功能矩阵、R05关系与测量边界；E18/35的研究限度。
- [选用包](../../../../../personal-learning-suite/resources/strategies/post/select-method.json)：完整特有正文及复用的相同指纹源段；识别／映射／执行分开；E11/12/13/15，变式与检索收益不混为单机制。
- [共同约束](../../../../../personal-learning-suite/resources/strategies/common-constraints.json)：两载体同源，H设计综合、无固定卡数／间隔／撤支持流程。

资源版本为pl-strategies/0.1.0；S05/D04源版本2.0；Post没有原卡ID，用suite方法键定位。已读内容用于设计选择，不在此次重做文献系统评价，不声称外部论文全文全部新核。上述研究／设计实际正文已由直接读取或包内原文完整取得；没有只凭策略名称实例化。

## 最近真实学习原件

有效轮次为2026-10-06-02及其续接2026-10-07-01。以下原件均实际回读，保持原位，没有复制为新表现：

| 原件 | 用途 |
|---|---|
| [首答](../../../sessions/2026-10-06-02/raw/M0-video-interface-001-initial.txt) | 已有尺寸／对应／未知区分及过推操作原因 |
| [两接口初答](../../../sessions/2026-10-06-02/raw/M0-video-interface-002-initial.txt) | B/T合并与起点布局问题 |
| [两接口修订](../../../sessions/2026-10-06-02/raw/M0-video-interface-002-revision-001.txt) | 组织与数值语义歧义 |
| [特征序列初答](../../../sessions/2026-10-07-01/raw/M0-feature-sequence-001-initial.txt) | 一行定位及来源条件判断 |
| [求助原话](../../../sessions/2026-10-07-01/raw/M0-feature-sequence-001-help-request.txt) | 对象、两消费者、来源恢复术语障碍 |
| [10-08修订](../../../sessions/2026-10-07-01/raw/M0-feature-sequence-001-revision-001.txt) | 保留视频分组，拆逐帧／置换／特征／信息混绑 |
| [同一事件revision3](../../../sessions/2026-10-07-01/event-M0-feature-sequence-001.md)、[checkpoint revision4](../../../sessions/2026-10-07-01/checkpoint.md) | 实际帮助先后及最新可信停止点 |

同时回读原Goal、旧题面及两份materials来源登记，以取得原规格与允许资料。没有读取其他对比备课的思路或答案；本成品的数值、材料、任务、参考与代码为当前模型自行构造。

## 本题技术核验

2026-10-08重新核对官方 [torch.permute](https://docs.pytorch.org/docs/2.14/generated/torch.permute.html) 的轴排列与 [torch.reshape](https://docs.pytorch.org/docs/2.14/generated/torch.reshape.html) 的同数据／元素数、view或copy限制；stable入口当时指向2.14。本地PyTorch版本未知，本次未运行PyTorch，也未安装依赖。

数据来自本例明示RGB表和空间加值规则。合法布局依据来自全坐标映射；g的信息性质来自选取定义及碰撞反例；来源恢复依据来自可信保序或完整随行标签。本例数值可查表与一般来源保证分别处理。教师标准库核查原件位于code/；运行输出保存在本备课目录verification.json，未记为用户代码、运行或学习表现。
