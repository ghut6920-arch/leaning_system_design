# 规则取得、策略实际采用与协作记录

版本 B1 / 2026-10-11。范围：本次独立测试备课；不接管原正式教学入口，不写真实进度或表现记录。

## 实际取得的规则

根 Agent 实际读取 AGENTS.md、state/control.md 当前revision11、state/current.md 当前revision22、MODEL_ENTRY.md、FRAMEWORK.md、START_PROMPT.md、INTERACTION.md；未沿旧待答引用读取历史学习作品。此次用户明确要求只备课，覆盖启动提示词中的正式教学动作。

共享语义按 `pl-contracts/0.1.0`；读取 SK00入口与session-entry、AG0/AG1/AG2/AG3职责，SK01及goal-design，SK03入口/disciplinary-to-teaching/design-whole/encoding/post-encoding，SK04入口/evidence-rules/product-review，SK05入口/planning及multi-scale-plan相关主干，SK06入口/selection-adaptation及索引候选。AG2研究子 Agent 另实际读取SK02入口、materials-workflow、domain-checks；结果与本轮来源/内容范围见两份研究原件。

研究/设计依据的正文由完整策略包取得：Encoding的R02、R03两载体，R01证据段；Post的D06对应恢复/关系/选用/条件更新正文、D07组合/实例化正文，R04矩阵和R05研究段落，以及R06证据条目。没有读取同主题旧备课实例、既有题解或历史方案；这些方法原文不是本单元历史成品。没有遍历全部策略库或使用synthetic程序。

框架核查实际使用manifest的 `entries`，119项SHA-256匹配，缺失/不匹配0。初次工具输出因误用 `files` 字段未形成有效核查；随后修正为entries并取得上述结果，未以失败结果宣称核查完成。指纹只说明当前文件一致，不能证明学科正确。

## 完整资源正文及本题采用

资源revision统一 `pl-strategies/0.1.0`；Encoding源版本2.0。所选完整正文、前置/排除/条件、必要操作、帮助反馈、停止返回、证据与时间约束实际读取。共用约束先取得；重复共用正文与Post重复源段按内容完全相同复用，独有正文仍读取。JSON排版/导航source_refs不重抄进成品。

| 资源键 | 本次实际借用的操作 | 落实位置、剩余工作与限制 |
|---|---|---|
| encoding/S05 | 正确范例的状态转换/理由追踪 | 输入§1–4：从attention行到逐层cache、资源模型与共享手算。借示范部分，不执行“遮答案后换数字”的固定训练；观看不记自主执行 |
| encoding/R04 | 分离联合条件、充分性与未确定 | 输入§2、§4、问题1：cache兼容、paging不能保证容量/质量/SLO；允许拒用和信息不足。没有制造学习者误概念 |
| encoding/R10 | 部件活动→交互→整体可观察结果，明确接口/边界 | 输入§4关系图、工程审查、连续服务备忘录：物理token/字节、时间、质量交集。图不是学习者作品；黑箱只在决定需要时打开 |
| post/retrieve-relation | 开卷前提下协调关系、方向、条件与整体 | 问题1及2：联合建模/容量/阶段指标。只借关系部分，不设闭卷恢复前测；支持后回同一备忘录 |
| post/select-method | 竞争情境下选择、拒用、映射、执行 | 问题2A–2B：澄清约束、构造候选、决定证据和接受规则。标题/主题/普通方法资料是可见线索，不能称无提示远迁移 |
| post/conditional-update | 定位新依据、保留旧合法域，修订当前条件 | 问题3U1/U2：共享域失效与新质量格反证；重新核容量、方法及承诺。不是擦除旧知识，不加延迟/复习债务 |

候选D09在索引中发现，但其并排策略比较与选用包在本题功能重叠，未调用完整D09，未声称采用。没有用卡名或compiled标志代替正文取得。教学方法研究的证据未在本轮重新核外部全文，其原历史条目按限定范围使用；当前学科解释与算例由专业来源、推导和代码核验支撑，未把教育论文当KV Cache正确性依据。

所用文件SHA-256：

```text
common-constraints.json e217a01ac8e71eae367cd4132cbc084c5c25d1f2a866341b05cacba6d15f3026
encoding/S05.json 75be952e8bc57ae87fe6d228cf1097f7dcf8db591987794578324c757fbeca36
encoding/R04.json 24606c5326153afb271a0280cd4fe1439dae34796af44d1c8eb667dd027fdde9
encoding/R10.json 16612c0a90f4a9fafe9f8e2e1da6f27d055ce0feed55cd56155433c4a147e597
post/retrieve-relation.json 9a40c98a6eddedc06cab02155aed54480c242f3f7bd2bbf70e116a0c87ec2dbc
post/select-method.json b33844944758174619f882a3131a60f3367782fcf88a94e3f2cb00eab2d022b8
post/conditional-update.json dd9ff6021b01147af7e8d51d610f1e5ba3174ccf7d0061903462f4ec2f4e9874
```

正文位置位于项目 `personal-learning-suite/resources/strategies/`，共享Skill规则位于 `personal-learning-suite/src/skills/`。上述资源在本测试采用，不宣称平台原生Skill安装、角色身份认证、并发隔离或正式学习计划生效。

## 实际研究、反馈及采用

| 实际执行者与所有权 | 实际返回与采用 | 边界 |
|---|---|---|
| discipline_sources：disciplinary-sources.md | 先从原用途研究缓存/IO/布局与改变函数的路线，核原论文/官方文档；主入口收到核心后才细化认知任务。主入口回问共享数值/64Ki执行与query工作；该Agent独立计数并补研究§9，主入口实际读回采用到输入§3–5与教师参考 | 未读旧备课；不由该Agent判断用户能力 |
| mechanism_audit：mechanism-analysis.md、demo.py、README、teacher-check-output.json | 返回因果逐层归纳、RoPE/位置、成本和数量；主入口采用这些连接，随后追加两层规范代码与运行委派。六prefix及三负例实际检查，版本1.0.0；主入口读回代码、说明、输出，不重复运行无变化检查 | 有限toy核验，不是FP8或GPU性能；两份研究不是独立学习样本 |
| root：主成品、visible-input/questions/teacher-reference/support、此记录 | 把学科依据转为一个连续决策作品、真实材料与教师多解参考。构造观测显式标识，未登记为真实实验 | 单一面向用户入口，当前仅备课交付 |
| reverse_review：review-questions.md、review.md | 原用途和必要规则/专业依据先取得，R1–R8先冻结；后续接到本次成品做反向实质审查，修复及最终结果见review.md | 实际独立上下文的子Agent，仍同模型体系；非真人/盲评，不证明协作收益 |

静态图、表、公式均围绕同一对象核对应关系；Mermaid源是两张关系图的规范可编辑形式，不声称进行了动画/交互测试。课堂材料先后与备用支持都是预备安排，今天公开审查不等于正式教学发生。

AG3首轮提出F1–F4，主入口实际修订并交回受影响段：adapter身份不同不能直接推出所有KV数值必然变化；服务p95明确样本对象、三次回放的池化口径及到达负载；同例加入R19真阳性使肯定结算确需联合两份记录，删B支持同步；公式排除限于相应全KV驻GPU候选，offload保留对应待证范围。AG3已局部读回，最终有范围结论见review.md。没有把这些准备修复登记为学习者错题或新增能力证据。

## 保护真实学习状态

开始时实际取得的SHA-256：

```text
state/control.md d7ba0aa3bf5c84b0a6888bbcccb48da66ddb7c3dbdc623daf31ff99b44692d87
state/current.md 0cdb6c945d41f929f66c9d1752403bb47b516e10ddd6fb763e160f84e3719977
```

最终读回及相对链接检查、这两文件一致性核对见verification.json。没有新增GoalSpec、PerformanceEvent、Judgment、LearningNeed、PlanCommitment或正式checkpoint；没有给用户虚构初答。备课成品、教师参考、教师运行、实际课堂和学习效果分别报告。
