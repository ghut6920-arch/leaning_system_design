# B3a／B3b／B3c 联合接口约定

日期：2026-10-03。本文件维护三个 B3 切片交界处的嵌套表示和阶段含义；共享对象及责任的唯一字段源仍为 [pl-contracts/0.1.0](shared-contracts.md)，保存仍经 [B1](runtime-b1.md)。不另建掌握度、事件、需求队列或数据库。

## 责任和调用顺序

| 切片 | 读取和产出 | 交界责任 |
|---|---|---|
| [B3c](strategies-b3c.md)／AG1／SK06 | 读取完整策略资源与当前工作；检查、采用和复用 MethodConfig | 配置规定计划保留的操作及帮助约束；不记录活动已经发生 |
| [B3b](teaching-b3b.md)／AG0／SK03/C0 | 读取合法 ActivitySpec、MaterialUse 及本次明确使用的配置；保存 PerformanceEvent 和断点 | 实际原答、帮助、修订、资源和时间覆盖计划声明；同题修订仍是一事件、一独立样本 |
| [B3a](assessment-b3a.md)／AG3 或获授权 AG0／SK04 | 读取选定响应点及确切历史条件；检查、提交 Judgment／DiagnosticNote | 按要求操作分别判断支持和资格；不重新发题、写事件或自动采用计划 |

可靠活动无选法需要时可以直接执行；有选法需要时先由 B3c 检查及专业采用，再由 B3b 复验本次引用，最后把同一事件与响应点交 B3a。三段可显式顺序调用；SK00 自动路由、专业接责和计划串接仍属 B5，真实身份与唯一展示执行者仍待宿主验证。

## 一个任务资格表示

`ActivitySpec.task_qualification` 为共享 Fact。当前规范表示如下；字符串列表必须对应活动实际要求的操作，四项检查均为布尔 Fact，不接受一般真值或把未知补成 true。

```json
{
  "status": "known",
  "value": {
    "target_operations": ["connect-P-to-Q"],
    "prerequisite_fit": {"status": "known", "value": true},
    "not_substituted": {"status": "known", "value": true},
    "reference_scorable": {"status": "known", "value": true},
    "evidence_conditions": {"status": "known", "value": true}
  }
}
```

资格表示题目是否调用受测操作、前置负担是否匹配、输入是否代做、参考能否评分及证据条件是否适用。它不是答题支持结论。计划中的 `not_substituted=true` 不能覆盖后来实际展示的帮助。

旧 B3b 的 `target_operation_call`、`prerequisite_burden` 保留保守读取适配：只有显式 known true 的调用声明才能按已有 `ActivitySpec.learner_operations` 解释其范围；前置负担声明映射为 `prerequisite_fit`。false／unknown 保持原状态。新旧字段同时出现而范围或检查互相冲突时拒绝，不择有利值。旧 B3a 缺 `not_substituted` 不自动获得“无代做”事实；独立资格仍须核实际时间线和完整性。新写候选使用规范表示，适配不改写历史对象。

## 响应点、帮助和时间

`PerformanceEvent.timeline_completeness` 为可选布尔 Fact。known true 仅表示记录者明确声明相关暴露已完整记录；缺字段、unknown 或 `prior_exposures=[]` 均不能证明无帮助。B3b 保存该声明，B3a 独立用途核它，不从打开材料成功或列表为空推导完整性。

评估始终选定 `conditions.response_points` 中的原答／修订 sequence。只核该点之前有关的实际展示与未知展示；planned／requested／backend_reference 不算实际帮助。代做只限制对应操作，未知展示按明确目标操作范围限定；缺范围时保持受测操作未知。后来帮助不追溯污染之前原答，帮助后的修订保留 assisted 范围，不增加独立成功样本。

父任务继承以 `c0.inherited_event_refs` 的确切修订追溯原事件和帮助，不能只用摘要宣称无帮助，也不能把父事件算成子任务的新表现。沿相关操作核继承暴露、接触和时间；未涉及本次受测操作的帮助不重置整个主题。父任务事实与子任务原答保持各自身份。

已知时间接受带时区 ISO 字符串或 known.value 中的 `timestamp`；unknown／缺时间保持未知。目标内延迟从选定响应点之前最近的相关接触计算，包含已有接触史、先前初答／修订练习、实际帮助／反馈及继承的相关事实。练习只参与接触时间，不被当作教师代做或新增样本。修订时间未知不能退回事件初始时间冒充修订发生时刻；先前练习或帮助时间未知不能用旧接触时间证明延迟。严格无接触仅在目标明确要求时检查。程序不从日历到期、排期或 time_condition=true 认证保持。

## 配置与材料用途的稳定连接

B3b 请求可给 `method_config_refs` 和 `strategy_context`。前者是本次明确使用的 MethodConfig 精确引用；后者沿 B3c 的 context，并包含完整 B2b `material_context`。B3b 对当前已采用配置调用 B3c reuse 复验，再把实际配置引用保存到事件。无需把新配置引用回写旧 ActivitySpec，从而避免“配置绑定活动修订、活动再绑定配置”造成循环失效。活动已有配置声明也必须经过当前用途检查，不能仅复制引用。

桥接检查配置的采用、绑定和控制条件；实际帮助仍独立记为发生事实。复用通过不证明执行完全遵守配置，也不能拒绝记录已经发生的偏离来隐藏帮助。B3a 按实际操作、暴露和时间限定证据；配置的 planned 约束不能覆盖事件中的实际条件。

未来执行要求当前、已采用且用途相容的配置；候选、旧版、删除／暂停／用途受限配置不能启动本次工作。历史评估仍引用当时实际配置的确切版本；配置升级不自动改写已发生原答、帮助或判断。历史读取仍服从删除和用途限制，精确历史可读不等于可作新的执行依据。

方法 purpose、材料 purpose 和判断 intended_use 分别回答“保留什么学习者工作”“该材料如何使用”“判断用于什么决定”。B3c purpose 为 teaching／independent，B2b material_context 为材料完整 binding，B3a 判断 purpose 为 assisted／independent，不能互相替代。方法为 teaching 不自动把材料的独立题面分区改为教学参考；实际帮助单独记入事件。完整材料 binding 的 activity_ref、goal_refs、intended_use、required_modalities、conditions、purpose 应与已核用途相容；supported 和 checked_revision 两个状态不足以替代用途复验。

B3b 的评估移交保留 `material_context`。B3a context 可以显式给此完整上下文，判断 intended_use 仍独立核授权；省略时沿旧 API 的同用途检查，不能由检查器猜造另一材料用途。B3c 当前输入适配为 `pl-strategies-input/0.2.0`，必须提供 material_context，且纳入 review_status.binding。旧配置缺该绑定时须 AG1 重核才能用于当前复用；历史版本保留，不自动迁移或重新采用。通用资源版本仍为 `pl-strategies/0.1.0`。

## 检查、采用、保存各有阶段

| 返回／字段 | 能说明的阶段 |
|---|---|
| 资源 compiled | 已有登记的完整包；不代表当前工作适配、有效性或执行 |
| 配置 reviewed | AG1 声明已审查且保留精确绑定；不等于专业采用 |
| B3c compatible／B3a compatible | 当前声明通过该切片检查；没有自动采用或执行 |
| B3c direct_reuse | 可靠旧活动无需新配置；没有造空壳 MethodConfig |
| B3c reusable | 已保存、显式采用的当前配置通过本次复验；尚未展示或发生学习 |
| B3b ready | 当前调用可继续；没有自动确认显示、评分或目标达成 |
| B3a submission_ready | 候选与有限条件结果一致，可以走受控提交；不等于 adopted |
| 判断 eligibility | usable／pending_review／withdrawn 说明所列用途的使用资格；不表示学习者掌握状态 |
| adopted／partially_adopted | 责任方明确采用／部分采用，须保留依据、范围、限制和时间状态 |
| committed | 原 B1 逻辑操作已保存；不等于专业正确、学习达标或计划已生效 |

`limited` 的具体后续由切片说明：B3c 必要条件未确认不能提交可用配置；B3a 可保存与受限结果一致的 unknown／pending_review 判断，过宽候选则 submission_ready=false。所有写入保留同一工作区、共享预算、CAS、幂等及精确依赖门禁。

现代授权的 validity 使用 known.value={active:true}；unknown、active=false 和任意非空对象不能冒充有效。显式开启 legacy 读取适配的入口可继续识别既有 B0 人工夹具的 prose validity；这只保持原夹具可读，不作为新授权模板，未知／false Fact 仍不能通过。fixture_actor／verified_for_fixture 仅限定虚构开发输入，不认证真实角色。专业核验、专业采用和专业用途恢复保持各自责任；更新版本、检查通过或保存回执不自动解除限制。
