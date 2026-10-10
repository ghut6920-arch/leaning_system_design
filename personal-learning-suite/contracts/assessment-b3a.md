# B3a 评估接口 pl-assessment/0.1.0

日期：2026-10-03。共享对象仍以 [pl-contracts/0.1.0](shared-contracts.md) 为唯一字段源，存储沿用 [B1](runtime-b1.md)，材料声明沿用 [B2b](materials-b2b.md)。跨 B3 切片的任务资格、历史配置、时序与阶段含义统一见 [B3 联合接口约定](b3-interop.md)。本文件只细化评估输入，不复制完整 schema。

`AssessmentService` 是虚构开发记录的声明检查器。模型依据 SK04 回原答、任务和判据作专业评分；程序检查引用、条件、实际帮助顺序、用途与授权，不判断任意学科答案真伪。`compatible` 也不证明学习目标已达成。

## 判断候选

`inspect_judgment(judgment, context)` 为只读。judgment 使用共享 Judgment 字段，增加 `conclusion`（授权内结论名称），`conditions` 采用以下精确表示：

```json
{
  "purpose": "independent",
  "response_points": [{"event_ref": {"id": "FIX-event", "revision": 1}, "sequence": 1}],
  "operation_findings": [{"operation": "connect-P-to-Q", "support": "supported", "rationale": "人工评分理由"}]
}
```

purpose 为 `independent/assisted`。每个事件恰有一个选定初答或修订点；多条件、多响应点分别出判断，但仍引用同一事件和样本。operation_findings 恰好覆盖当前 requirement.key_operations；评分理由必须来自专业方，不由检查器猜造。顶层 support 按这些操作的受条件限制结果汇总：全部 supported→supported，全部 observed_not_met→observed_not_met，全部 unknown→unknown，其余→mixed_or_conflicting。检查器返回 `operation_conditions` 和 `expected_support`；不静默改写调用者判断。

context 为 `{intended_use, review_triggers, review_resolution?, material_purpose?, material_context?}`；intended_use 必须属于 Judgment.intended_uses，表示判断的决定用途。material_context 如提供，应为完整 B2b 材料用途上下文，保留活动／目标／用途／模态／条件／purpose；材料用途和判断用途分开检查，不能用 assisted／independent 评分目的替换材料 binding。省略时保留旧 API 的同用途匹配，不猜造另一材料用途。review_triggers 是显式列表，不能以缺字段表示无升级信号。重要跳过、整体复杂产物、新解法、评分争议、反证、删除影响和结论扩展只能由 AG3 professional_review 处理。程序还检查标准用途信号、已有反证和授权声明的升级信号，不能通过空触发列表绕过。冲突解决须有 `review_resolution: {rationale, reviewed_refs}`，覆盖相反旧判断（包括同一稳定 id 的旧修订），不能通过多数票或最后到达解除。

ActivitySpec.task_qualification 沿联合约定：known.value 为 `{target_operations, prerequisite_fit, not_substituted, reference_scorable, evidence_conditions}`；后四项是布尔 Fact，未知保留原因。旧 B3a／B3b 表示仅按显式声明保守适配，双字段冲突拒绝。事件的 `timeline_completeness: Fact` 为 known true 时只说明记录者声明相关暴露已完整，不认证宿主；缺声明或暴露空列表不能证明独立无帮助。timeline 本身保留共享 ExposureEvent；只计算选定响应点之前的 displayed 和 unknown 暴露，planned/requested/backend_reference 不作为实际帮助。父任务 inherited_event_refs 按确切历史修订回查，不能忽略继承帮助或把摘要当无帮助证明。代做只影响对应操作；未知展示按 target_operations 限定，空操作范围保持受测操作未知。帮助后的修订可支持 assisted 范围，自主操作另列未支持，不丢帮助前原答。

必须回查选定 original_response 或 revisions 的 ArtifactRef，原件可按 `start_line/end_line` 显式限定；没有行段时仅核查合法原件引用及定位，不宣称模型已读正文。材料 content/use 必须分别 supported、checked_revision 与引用修订一致，use.binding 匹配明确的材料上下文；旧调用不提供 material_context 时仍核 goal_refs/activity_ref/intended_use/conditions 及 material_purpose 的原规则。帮助后的判断可以在材料已核用途范围内使用原任务独立题材参考，实际帮助单独解释。它们只是 AG2 声明。原任务调用不到目标操作、前置负担不匹配、参考不能评分，限制对应判断。

GoalSpec.time_requirements 为 not_required 时不生成时间缺项。known.value 在本切片为 `{requirement_ids, minimum_delay_seconds, require_no_contact}`；事件 occurred_at、响应点 time 及 contact_history 使用联合约定的带时区时间表示，contact_history 为 known.value `{last_relevant_at: ISO时间或Fact, intervening_contact: Fact}`。延迟从选定响应之前最近相关接触计，涵盖实际帮助／反馈及相关继承事实；未知帮助时间或修订时间不退回较早已知时刻。缺失保持 pending_review，绝不从当前日历到期推断；严格无接触仅在 require_no_contact true 时检查。时间资格未满足时，对该时间用途的 expected_support 为 unknown，同时 operation_conditions 保留当前作答的正面观察。这是开发输入表示，未实现时间调度或自动观察。

返回 status 为 compatible/limited/rejected/blocked，含无正文错误码、state_revision、操作级条件、唯一样本 ID、未支持范围、`submission_ready` 和 `next_action`。compatible 只代表当前声明可审查；limited 可以给出过宽候选的操作级范围，但 submission_ready=false 时不能保存。允许保存与有限结果一致的 unknown/pending_review 判断，绝不静默改写原候选。始终 `mutated=false`；不生成新题、PerformanceEvent、LearningNeed 或计划。授权主体／决定／结论的预检先于加载表现及整份上下文；正式当前依据还检查递归材料、来源、活动及预算修订。事件当时使用的 MethodConfig 沿精确历史引用读取，不因后来配置升级要求把历史事实改成新版；历史合法性和新的执行资格分开，删除及相关用途限制仍生效。递归旧决定依据返回重核，原历史事实不改写；当前 B1 不能恢复专业用途门，存在该门时不宣称重评已生效。

## 授权、诊断和保存

### 目标版本与历史回查的当前边界

`read_refs` 和原件读取保留仍合法的精确历史修订；目标的新修订不改写当时任务、原答、帮助或旧判断。`inspect_judgment/submit_assessment` 检查的是拟用于当前决定的判断，依赖仍须满足当前专业采用及版本条件。`GoalSpec.version_compatibility` 的 `preserve` 声明不能单独迁移 Judgment，也不能绕过旧活动、参考、授权及材料用途的重核。

2026-10-04 的版本边界检查覆盖等价说明维护、声明兼容但未采用迁移，以及判据实质更正：历史回查保持可用，未经重核的当前判断返回 `stale_assessment_dependency`，旧事实保持原样。当前尚没有正式的跨目标修订支持迁移或历史重评提交接口；需要该能力时须明确原条件、当前用途、映射与评估责任，而不是关闭最新依据门禁。这一能力限制不等于原证据被删除或学习者能力下降。

AuthorizationGrant 的 grantee/decision_types/object_scope/criterion_refs/conclusion/budget_ref/binding_status 均检查。实际活动预算须与授权引用相同。AG0 仅 routine_scoring 或显式 limited_diagnosis；AG3 的 professional_review 不由 Skill 模式授予。新授权不能通过该组件创建。模板 [常规评分授权](../templates/routine-scoring-grant.json) 为 unbound，不能直接执行；已导入的人工 fixture 授权仅适用于开发验证。validity 本切片要求 `{status: known, value: {active: true}}`；不实现真实身份或自动时钟失效。

`inspect_diagnostic(note, context)` 检查观察引用、授权、替代解释、反证、至少两个观察→不同安排的分支、预算、停止与重开条件。context 必含 `intended_use/conclusion`，可声明 stop_signal=budget_exhausted/no_progress/no_decision_value/user_pause。已确知无反证允许空列表，缺失／null 不表示无反证。若 next_observation 明确 not_required/not_executed、预算为零或当前停止信号成立，返回“不追加观察”，不会发题；诊断仅为暂定解释，不创建稳定用户画像或安排。

`submit_assessment(request)` 只接收同一 fixture_actor 的 Judgment/DiagnosticNote；request 携带 B1 的 expected_state_revision、operation_id、authorization_refs、adoption_refs、changes，以及按对象 id 索引的 contexts。先检查所有依赖的 assessment 门和实际用途门，再执行条件检查，最后调用原 store.commit；失败不落正文。compatible 或与受限结果一致的 limited 可以提交。不得夹带事件、需求、授权、材料或计划，不能恢复专业限制。候选与采用保留共享 adoption，检查成功不自动 adopted。

```powershell
python -X utf8 personal-learning-suite/src/runtime/learning_assessment.py --workspace "examples/workspaces/B3a_虚构证据学习空间" --request request.json --actor AG3 inspect
```

CLI 命令 inspect/diagnose/submit；actor 是测试配置，不是宿主认证。请求文件和 stdout 属调用者副本，SQLite 删除无法清它们；错误结果不回显原件正文。B3b 教学共同核心和 B3c 配置现已有显式调用接口，联调范围见联合约定；B5 自动接责／路由／计划、真实宿主及完整 B10/V1—V4 验证仍待后续批次。
