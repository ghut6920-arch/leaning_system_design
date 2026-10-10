# B2a 独立前向试用记录

日期：2026-10-03。执行者：开发子代理，未绑定宿主，未部署为 AG1/AG2/AG3/AG0。只使用 [原始人工虚构输入](fixtures/raw-input.md)，没有读取既有 B2a 目标夹具的预设答案。

先读取 `learning-goals/SKILL.md`、共用契约、目标设计及版本规则，再产生 [原始语义候选](candidate.semantic.json) 和 [原始会话变更视图](session-change.semantic.json)。随后读取公开 B2a 适配接口并用 [适配脚本](adapt-and-run.py) 生成 [CLI 初始输入](input.json) 与 [CLI 会话变更输入](input-session-change.json)。适配保留最初请求和候选文本，只转换公开接口需要的 Fact、读清范围、逐要求证据、范围及前置字段表示。

实际执行：

```powershell
python -X utf8 personal-learning-suite/validation/b2a-forward/adapt-and-run.py
```

脚本分别调用两次 `src/runtime/learning_goals.py --input`，原始 stdout 保存在 [初始输出](raw-output.json) 和 [会话变更输出](raw-session-output.json)；两个 `.stderr.txt` 为空。精简实测值在 [actual-checks.json](actual-checks.json)。这不是复制预设期望的验收报告。

| 实际观察 | 初始请求 | 3 分钟、先看示范变更 |
|---|---|---|
| CLI 退出码 | 0 | 0 |
| `review_state` | `partial` | `partial` |
| `errors` | 空 | 空 |
| 结构与人工核验声明支持的要求 | `write-xor-rule`、`explain-equal-inputs` | 同两项 |
| 目标 ID / 修订 | `FIX-FWD-goal-xor` / 1 | 原 ID / 1，整个目标与初始候选完全相同 |
| 两项 `criterion_revision` | 各 1 | 各 1 |
| 正式时间要求 | `not_required` | `not_required` |
| 版本处理 | 首个候选，没有旧版本比较 | `preserve`，没有 Judgment 搬运 |
| 计划处理 | 没有计划交接 | SK05/AG1 候选交接，`valid_commitment=not_created` |

`partial` 来自已明确保留的四项未决：具体配置语言、官方考核、正式材料用途资格、实际任务和帮助条件核查。它们没有把“证明”和“硬件设计”变成进入近期目标的门槛。本候选支持的只是虚构的语言无关异或语义与解释；具体配置平台执行已明确列为未覆盖范围，所以未决项没有封锁这两项候选语义要求。

原始候选把两项要求均标为个人 `user_purpose`，没有发明官方课程标准。资料 A 支持“为何需要这两项能力”，资料 B 支持布尔域和异或正确性；目标、两项判据和前置均保留具体修订双来源。手工枚举四输入只检查虚构定义的内部一致性，没有写成学习者表现或实际 AG2 回执。

证据设计允许布尔语法文档，要求关键规则组织及解释由学习者完成；同一原始草稿可支持可辨认的两项操作，但不会变成两个独立样本。没有把闭卷背诵、延迟保持、陌生迁移或硬件实现添加成要求或复习债务。学习者前置状态为未知，“没有学习历史”没有被推断为不会。

会话变更保留完整目标与判据，只把 3 分钟交计划方，把示范交材料及受控教学入口。示范在独立视图中为 `requested`，实际显示为 `not_executed`；没有生成学习者原答、PerformanceEvent、Judgment、掌握状态或有效 PlanCommitment。若未来显示完整示范，直接复制只支持相应帮助条件，这属于后续真实接触记录及评价工作。

发现的接口限制和仍无法判定处：

1. 辅助程序依赖输入的 `supported_for_fixture` 手工声明，既不复现手工枚举也不核学科内容；本试用不能据程序的 `reliable_requirement_ids` 宣称正式参考资格、内容被独立核验或能力已达标。
2. 公共对象允许的宽泛表示需要适配为本切片更窄的嵌套格式。原始语义候选的双要求综合证据要拆成逐要求字段；脚本显式保留“同一综合草稿、不增样本”以免转换丢掉综合关系。
3. 来源 locator 是语义定位，不是程序验证的 JSON Pointer。资料 A 的原 `claims/near_scope` 标签在转换后的声明字符串中仍能由人定位，但程序没有核对该 locator。未检验定位错误的拒绝能力。
4. CLI 报告保留目标来源引用，但没有将完整 `sources` 回传为独立 P-Goal 来源包。脱离输入而单独消费 stdout 时，接收者不能仅靠输出解析全部来源。此试用的完整交付以原输入及原始 P-Goal 视图一起为准。
5. CLI 的计划交接使用通用措辞“保留正式目标”，但本输入仍是候选目标；其边界字段明确 `professional_adoption=not_executed`。通用措辞不能提升采用状态。
6. 3 分钟值及示范 `requested` 状态保存在独立会话视图和输入额外字段；程序没有专门处理示范事实，也没有把结构化预算传入输出。实际交接需要同时带上 [会话变更视图](session-change.semantic.json)，不能从输出误判示范已展示或计划已接责。

本次只观察到一个独立虚构请求可以经 Skill 形成有来源和边界的候选，并经辅助程序读入、比较和交出缩时处理候选。还不能判断真实课程有效性、真实权限隔离、运行协作增益或学习成效；未检验陌生语言、官方评分冲突、真实用户删除和正式采用。以上不足保持明确未证，没有用其它测试成功替代。
