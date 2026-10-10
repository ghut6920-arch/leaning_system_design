# B5 单入口纵向接口

日期：2026-10-03；入口版本 `pl-entry/0.1.0`。共享对象保持 [pl-contracts/0.1.0](shared-contracts.md)，保存继续使用 [B1 LearningStore](runtime-b1.md)。本接口只串接已实现的专业服务，不另建字段定义、数据库、角色身份或学习队列。

入口为 `runtime.entry_b5.SingleEntryService(store).execute(envelope)`，由 `PersonalLearningEntry.execute(request)` 暴露。入口 Store 必须为 `entry_actor=AG0` 的明确虚构工作区；角色字符串仍是测试配置，不是真实认证。`start/resume/route` 原有只读语义保持。

## 请求与串行步骤

`envelope` 必需字段：

| 字段 | 含义 |
|---|---|
| `entry_version` | 必须为 `pl-entry/0.1.0` |
| `synthetic_only` | 必须为布尔 `true` |
| `expected_state_revision` | 本次进入时读取的非负整数状态修订；读取步骤也需显式根 CAS |
| `steps` | 1—32 项，按列表顺序调用；不自动补步骤 |

每步为 `{id, operation, request, bindings?}`。`id` 为非空、最多 80 字符、链内唯一的标签；`operation` 必须在下表中；`request` 为该专业服务的对象。写步骤必须提供非空、最多 200 字符、链内唯一的 `request.operation_id`，不能含空字符。步骤不接受自报 `actor/entry_actor` 或 `expected_state_revision`；专业 actor 由动作映射，写 CAS 由根修订及前步实际提交结果注入。

单给 `{"intent":"评分"}` 且无 `steps` 时，只返回 `needs_input` 与旧 `route` 候选，要求明确专业步骤，不执行、接责、保存或开课。

## 允许动作与专业责任

| `operation` | 专业责任与 `request` |
|---|---|
| `goal.review` | AG1；`{package}`，调用 B2a 候选检查 |
| `goal.sources_submit` | AG2；`{package, changes, operation_id, authorization_refs?, adoption_refs?, artifacts?}`；完整检查原目标 package，只提交其中完全一致的 SourceFragment |
| `goal.submit` | AG1；`{package, changes, operation_id, authorization_refs?, adoption_refs?, artifacts?}`；先复查 package，再经 Store 保存 |
| `need.submit` | AG1；`{changes, operation_id, authorization_refs?, adoption_refs?}`；只保存新 ID、`acceptance.status=proposed`、`disposition.status=pending` 的 LearningNeed，不接责或安排；已有需求更新交计划服务 |
| `materials.read` | AG2；原 `read_fragment` 请求：片段 ID、来源身份、ArtifactRef 和显式行段；提取返回候选，语义核验仍待做 |
| `materials.inspect` | AG2；`{material, context}`，只读用途／核验声明检查 |
| `materials.submit` | AG2；原材料提交请求，含 `changes/context/operation_id` 与授权、采用引用 |
| `strategies.inspect` | AG1；`{config, context}`，只读配置检查 |
| `strategies.reuse` | AG1；`{config_ref, context}`，复验当前已采用配置，成功不启动教学 |
| `strategies.submit` | AG1；原配置提交请求，含 `changes/context/operation_id` 与授权、采用引用 |
| `teaching.run` | `design/commit_design` 使用 AG1；其他允许教学动作使用 AG0；`request` 直接沿用 B4 教学请求 |
| `assessment.inspect` | AG3；`{judgment, context}`，只读判断候选检查 |
| `assessment.diagnose` | AG3；`{note, context}`，只读有限诊断检查；不追加测验 |
| `assessment.submit` | AG3；原评估提交请求，含 `changes/contexts/operation_id` 与授权、采用引用 |
| `assessment.routine_inspect` | AG0；`{judgment, context}`；只在有效常规评分授权范围内检查 |
| `assessment.routine_submit` | AG0；同评估提交结构；重要复核信号仍由专业服务阻止常规采用 |
| `planning.inspect` | `request.action=shrink` 使用 AG0，否则 AG1；原计划请求，只检查候选 |
| `planning.run` | `request.action=shrink` 使用 AG0，否则 AG1；原计划请求，写步骤含 `operation_id` |
| `planning.resume` | AG1；`{commitment_ref}`，只读恢复当前承诺及合法依据 |

专业输入的必需细节仍按 [B2a 目标](runtime-b2a.md)、[B2b 材料](materials-b2b.md)、[B3a 评估](assessment-b3a.md)、[B3b C0](teaching-b3b.md)、[B3c 策略](strategies-b3c.md)、[B4 教学](teaching-b4.md)、[B4 计划](planning-b4.md) 和 [B3 联合约定](b3-interop.md)；此表不免除原服务检查。

`goal.sources_submit` 承接 B2a package 中的来源 Fact 表示，完整 review 须完成，changes 只含与 `package.sources` 完全一致的 SourceFragment。原核验声明原样保存，不转换为 B2b 的模态字段，也不把 B2a 结构检查升级成内容核验。来源仍由 AG2 携相应授权保存；人工 artifacts 仍经 Store 原件检查。

推荐先 `goal.sources_submit` 保存来源，再 `goal.submit` 只提交一个 GoalSpec。目标除 `adoption/authorization_ref/decision_type` 三项显式采用字段外须与 `review.goal_candidate` 完全一致；三项由调用方提供，入口不自动加正式采用。goal.submit 若附 SourceFragment，仍必须与 package.sources 一致且符合 AG2 专业归属与授权，不能由 AG1 代写来源。允许保存候选目标不意味着可以执行教学。

当 package 中定义的 SourceFragment 或 GoalSpec 已有相同精确引用时，须与已保存对象一致；GoalSpec 只对上述三项采用字段作允许差异，SourceFragment 不作字段豁免。不能替换来源正文、核验声明或目标内容后仍借用旧 ID／revision。

显式 `decision_type` 须与对象的专业责任相符：GoalSpec 仅 `goal_design`；SourceFragment 为 `material_read/material_review/material_verification`；MaterialUse 为 `material_use/material_review/material_verification`；MethodConfig 为 `teaching_design/strategy_configuration`；Judgment 为 `routine_scoring/professional_review`；DiagnosticNote 为 `limited_diagnosis/professional_review`。不能通过给目标伪标 planning 决定来消耗其他授权；Store 仍复验授权、范围与采用依据。

`teaching.run` 当前允许 `open/resume/design/select_branch/review_whole/reuse_evidence`，以及写动作 `record_initial/record_help/record_revision/record_feedback/checkpoint/close/return_parent/commit_design/enter_local/return_local`。专项由 B4 检查，C0 保存原答、真实帮助和断点；入口不把准备好的参考当作已展示。

## 已有输出的精确绑定

`bindings` 把本步 `request` 内已有位置替换为此前成功步骤的返回值，结构为：

```json
{
  "/judgment/basis_refs/0": {
    "step": "save-initial",
    "path": "/output_refs/0"
  }
}
```

本例要求本步 `request.judgment.basis_refs[0]` 已存在，常用 `null` 作显式占位；源指针相对前步 `result`，而非整条 step 回执。目标／源采用 JSON Pointer 的 `/`、`~0` 和 `~1` 转义。不能引用自身或后步，不能制造不存在的字段，不能通过绑定修改路径任一层的 `operation_id/expected_state_revision/actor/entry_actor`，也不能替换顶层 `action/synthetic_only`。绑定中的源路径在实际取得前步输出后检查；无值则该步失败，后续不执行。

保存后引用以正式 `output_refs` 为准。候选内容可以传给另一候选检查，不能冒充 Store 中合法已保存对象；正式后续动作继续复验引用及采用。入口不按字符串模板猜引用，不把所有步骤预先改成同一状态修订。

## CAS、失败与重试

根 CAS 过期时，整条链在开始前返回 `conflict`，不会自动重放或续跑。每步开始重新读取状态，与已确认的修订不符即停止；一个新提交或只读幂等回执之外的状态变化不能被当成自己的推进。

每个专业写步骤自身是原 Store 事务，**整条链不是原子事务**。中间失败后保留实际已提交的前缀，返回 `partial`；没有保存前缀时返回失败步骤状态。失败步骤和后续未执行步骤不提供虚构保存／采用回执。继续须先重读当前控制与修订，提交经复核的剩余步骤；单步骤可以在当前根 CAS 下使用原 `operation_id` 重试同一专业请求。不会保存另一份链进度日志，自动后台续跑不在本批范围。

删除、暂停、用途限制、授权、精确版本和预算沿原专业服务／Store 检查，不能通过旧操作成功回执解除当前控制。程序不认证学科内容真伪、评分正确性、真实成本或实际显示。

## 返回阶段与学习者视图

顶层返回版本、`mode=single_entry_sequential`、状态修订、`mutated`、逐步回执 `steps`、已保存 `output_refs`、`pending`。成功 `completed` 仅表示请求中的全部调用返回可继续状态，不等于目标已达成、全部产物已正式采用或需求已安排。

每步保留原专业 `result/status`，另外标出 `stage`：`saved` 只对应 `committed`；`candidate` 为候选；`limited` 保留条件限制；`checked` 为其他可继续检查结果；`pending` 为失败或未满足条件。专业 `ready/compatible/reusable` 不自动变为 `saved`。评估的 `limited` 仅在原服务明确 `submission_ready=true` 时可继续；目标候选只有 `review_state=complete` 才可继续。`mutated` 反映本次状态是否实际改变，幂等已保存回执可能 `stage=saved` 而 `mutated=false`。

失败和未处置教学后续生成 `pending` 中的 `owner/decision_needed/next_trigger`；专业 `unresolved_items` 按原结果保留，不能把它们升级为已接责。close 后续候选若引用已有需求，入口只在同链 `planning.run` 实际保存该稳定需求的非 pending 去向后清除对应 pending；仅收到、接受或保存新提出需求仍未处置。`unexecuted_steps` 列出失败后未调用的步骤 ID。

`user_view` 提供当前工作阶段及原服务预算视图、已保存活动事实、条件化支持、需求的真实接责／去向四类内容及当前控制，避免把学习发生、证据支持和有效安排混为一条完成状态。需求仅包含本次请求关联的需求 ID 或目标范围，带 `goal_ref`，不会展示其他课程的全部需求；判断带目标及 requirement 定位。视图不复制教师参考或原答正文；原专业 `steps[].result` 可能含读取文本或候选，因此完整技术回执不能不加选择地直接展示。

`background_delegation/host_identity_verified/learning_effect_verified` 均为 `false`。本入口不创建网络工作单、自动接责、提醒、独立复核或宿主展示拦截；这些能力按 B6／B7 后续验证。

## CLI

```powershell
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构工作区目录> execute --request <UTF-8请求.json>
```

读取 UTF-8／UTF-8 BOM JSON。完整步骤沿上述 envelope；`completed` 返回零退出码，`partial/conflict/rejected/blocked/not_saved/needs_input/limited/not_ready` 返回非零。真实个人学习空间仍被拒绝，stdout 和调用方请求文件属于共享数据库外的副本。
