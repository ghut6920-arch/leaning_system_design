# B3b C0 教学运行切片 pl-teaching/0.1.0

日期：2026-10-03；共用协议保持 `pl-contracts/0.1.0`，保存承载保持 `pl-store/0.1.0`。本专业协议只定义 TeachingService 的请求与运行边界，共享对象字段仍以 [shared-contracts.md](shared-contracts.md) 为唯一维护源，跨 B3 的资格、配置、帮助与时间统一见 [联合接口约定](b3-interop.md)。不另建事件、掌握度、需求队列或数据库。

## 交付范围

[learning-teaching](../src/skills/learning-teaching/SKILL.md) 指导 C0 的活动候选设计及授权执行。[TeachingService](../src/runtime/learning_teaching.py) 读取已有 ActivitySpec 和当前目标／材料／控制，保存 PerformanceEvent 与 SessionCheckpoint 的事实修订，并返回原答条件、评估移交和同一需求的更新候选。它不生成／采用 ActivitySpec，不写 LearningNeed 或 PlanCommitment，不提交正式 Judgment 或 DiagnosticNote。

B3a 已提供独立评估／诊断和受控提交接口；C0 返回显式评估移交，不自动提交正式判断。当前请求可经 B3c 复验明确采用的配置，再保存实际条件供 B3a 检查。Encoding／Post 专项执行器、SK05 计划、B5 自动接责与路由、四角色宿主绑定及并行展示隔离不属于本切片。检查 task_qualification、材料核验声明及精确引用相容，仅证明当前声明通过检查，不能证明题目正确、用户独立掌握、AG3 已复核或真实教学有效。

只处理显式虚构工作区与 `synthetic_only: true` 请求。测试角色与授权使用 `verified_for_fixture`，不认证真实 AG0 身份。全部写入经原 LearningStore.commit，使用同一 `records.sqlite3`；请求文件、stdout、宿主界面和已加载上下文不在 SQLite 删除范围。

## 请求入口与当前动作

调用 `TeachingService(store).run(request)`；CLI 从 UTF-8 JSON 请求文件读取，不按子命令决定动作：

```text
python personal-learning-suite/src/runtime/learning_teaching.py --workspace <虚构开发记录目录> --request <C0请求.json>
```

公共载荷包含 `synthetic_only: true`、`action`、当前精确 `activity_ref` 与 `context`。context 沿用 B2b MaterialUse 的用途 binding：`activity_ref`、`goal_refs`、`intended_use`、`required_modalities`、`conditions`、`purpose`；内容与用途均须支持当前活动。使用配置时另给 `method_config_refs` 和 `strategy_context`；strategy_context 为 B3c 的当前 context，内含完整 material_context，并与本次活动／目标／材料／预算及 context 精确对应。B3b 经 B3c reuse 检查当前已采用配置，将实际引用保存到事件，不回写 ActivitySpec 造成修订循环。活动预存的配置引用也不能绕过复验；无配置的可靠活动可以直接执行。写动作额外给明确 `expected_state_revision` 与 `operation_id`，原答等受控原件通过请求的 `artifacts` 进入同一事务。当前角色授权、预算、精确依赖和提交字段遵循 B1／共享组件，不因 action 名称扩大权限。真实执行代次与旧输出拦截仍需 B6 宿主落实。

| action | 支持的有限工作 | 不代表什么 |
|---|---|---|
| open | 读取当前活动与 learner_packet，检查当前可执行用途 | 未确认宿主实际展示，不计新暴露或学习事件 |
| resume | 核当前依据及可信断点，返回合法继续位置 | 不补造未记录最后动作，不重做完整冷启动 |
| record_initial | 保存原答、事件身份、实际资源与已知时序条件 | 不评分、不从原答文字推测掌握或未知接触 |
| record_help | 追加帮助／展示事实及其目标／代做操作 | planned／requested／后台参考不冒充 displayed |
| record_revision | 同一表现追加修订，保留原答和样本身份 | 不新增独立成功，不把修订回写成初答 |
| record_feedback | 用既有分支和原答定位记录反馈依据／工作 | 不自动诊断原因、不生成新任务或补测 |
| checkpoint | 保存当前可信事件、父产物与下一连接、停止原因 | 不宣称整体完成或变更目标 |
| close | 保存收束事实、未完成的目标内要求与责任触发 | 不产正式目标通过或排程承诺 |
| return_parent | 返回同一父活动及规范产物连接 | 局部成功不自动使整体通过 |

`open` 的 learner_packet 只返回 ActivitySpec.prompt 与 MaterialUse.visible_input，不包含 backup_help／teacher_reference。调用方把某条帮助提供给学习者后，应照实际内容和可确认的 visibility 记录；读取成功不等于实际展示，宿主不明保持 unknown。

### 各动作的载荷

| action | 动作专有字段 |
|---|---|
| open | 公共 context 即可；可用[虚构只读请求](../fixtures/b3b-open-request.json)查看演示空间 |
| record_initial | `event_id`、`independent_sample_id`、`original_response`、`artifacts`、`initial_response`、`contributors`、`occurred_at`、`contact_history`、`actual_resources`；可给 `prior_exposures` 保留初答前题面／标题／帮助的实际声明，另用 `timeline_completeness: Fact` 明确相关暴露是否完整 |
| record_help | 精确 `event_ref` 与 `help`；只有实际确认显示才用 displayed，其余按实际状态保存 |
| record_revision | 精确 `event_ref`、`revision_response`、`artifacts` 与 `revision`；每次修订使用新原件路径 |
| record_feedback | 精确 `event_ref`、`branch_index`、`observation: {artifact_ref, quote}` 与 `feedback`；观察只能定位该事件的原答或修订 |
| checkpoint／close | 精确 `event_ref`、`checkpoint_id`、`stop_reason`、`next_connection`、`pending_owners`、`unrecorded_actions`；close 再给 `closure: {status, reason}`、`unfinished_requirement_ids`，必要时给 `existing_need_ref` |
| return_parent | 精确 `event_ref`、与现有 ParentTask 一致的 `parent_ref`、`parent_artifact`、`return_connection` |
| resume | 精确 `event_ref` 或 `checkpoint_ref`；由指定可信修订恢复，不暗取对象排序的最后一项 |

`initial_response/help/revision/feedback` 包含 `content`、`visibility`、`target_operations`、`substituted_operations`、`time`；time 是共享 Fact，操作必须在当前活动范围内。`prior_exposures` 元素沿用这些字段，并可指定 `kind: exposure/help`。实际发生的 sequence 由助手按追加顺序生成，原件路径保留在对应 timeline 项。`original_response/revision_response` 是 `origin: synthetic_fixture` 的 ArtifactRef；已有原件的观察读取还须明确 `start_line/end_line`，不以整文件摘要代替原答。

close 的 `closure.status` 可为 `local_sufficient/budget_end/no_feasible_branch/unfinished`，只描述本次活动停止类别，不表示目标正式通过。未完成要求限于该活动已绑定的要求；父任务整体的尚未完成工作另保留在同一 ParentTask 及规范父产物。已有需求回传候选与保存回执分开，不能通过增加 event_ref 把候选变为已安排。

已知 time 使用含时区的 ISO 时间字符串，或 `known.value.timestamp`；已知顺序须非递减，逆序返回 `timeline_time_order_conflict`。未知时间仍保留 sequence，不能给它补造钟表时间。迟到发现的初答前帮助不能按“现在追加”假称发生在初答后，应返回核对时序，当前切片没有重排旧时间线的勘误动作。

`active_minutes` 可由调用方声明为当前累计分钟数，必须有限、非负，后续不能回退；缺省保存为 `declared_active_minutes: unknown`，已有数值不会因省略参数归零。预算已到时停新展开，允许 checkpoint／close 保存收束；该声明不是程序计时器或完整跨活动费用账本。父任务已知帮助通过 `parent_help_history_refs/parent_help_conditions` 保留，事件的 `c0.inherited_event_refs` 引用转入前事实，不另造样本；B3a 按这些确切事件和本次操作核继承条件，不只读摘要。

checkpoint 提供新的累计时长时，PerformanceEvent 与 SessionCheckpoint 在同一事务保存相同声明，检查点指向该次更新后的事件；事务失败两者均不生效。恢复仍按显式历史响应点读取原答、帮助和断点，预算累计下界另取当前同活动、同预算、同事件身份的合法记录最大值。旧检查点较高时长可以补足修复前记录的预算下界，不将其中旧教学决定、旧帮助条件或旧目标当作当前依据；无关活动／预算或不能绑定事件的检查点不进入下界。匹配本次耗用的检查点受控不可用时，返回 blocked，不读出受限事实也不将其当作零支出。打开、追加帮助和再次保存声明不得退回旧额度；现有记录不作批量历史重写。

## 资格、事实及控制

当前 ActivitySpec.task_qualification 使用联合规范的 known Fact：`target_operations` 为明确字符串列表，`prerequisite_fit`、`not_substituted`、`reference_scorable`、`evidence_conditions` 均为布尔 Fact。旧 B3b 的 `target_operation_call`／`prerequisite_burden` 保守适配，不补造 true，不接受非布尔真值；新旧声明冲突拒绝。资格声明独立于答题好坏，未知或不满足时限定用途，不能答对后追认合格。计划的“不代做”不能覆盖实际帮助。只有实际需要的资源／模态和目标内时间条件才参与本次判断。

PerformanceEvent 原答与修订为可回查 ArtifactRef，事件与 `independent_sample_id` 保持稳定。实际原件不可原地覆写；帮助、反馈和修订按 sequence 追加并保留时间 Fact。ExposureEvent.visibility 保持共享的 `planned/requested/displayed/backend_reference/unknown`；只有 displayed 是已确认展示的事实。timeline_completeness 为显式布尔 Fact；省略、unknown 或 prior_exposures 空列表不证明暴露完整，也不证明无帮助。备用参考未显示不计暴露。

当前条件说明按代做操作保留事实：提供前提不替代之后所有推理，完整方法示范不成为学习者自主选择证据。原答初答前后顺序、实际资源、初学／最近相关练习反馈和再接触已知性分别保存；未知不补造，日历到期不能证明延迟条件满足。该条件说明供评估移交，不能代替正式 Judgment 的支持／资格双轴。

配置复验只检查当次采用／绑定／控制，不证明实际执行完全遵守计划；已经发生的帮助或偏离仍如实追加，不能因配置禁止它就删去事实。实际帮助可能限制独立证据，交由 B3a 按操作和选定响应点解释。

SessionCheckpoint 引用最后可信 PerformanceEvent、帮助历史和规范父产物，记录 next_connection、stop_reason、pending_owners、budget_ref、control_ref 与 unrecorded_actions。父任务沿用原 ParentTask 的卡点、替代解释、局部够用条件及 return_connection，不复制父产物或重置原暴露历史。

提交先检查删除／暂停／用途限制，再核当前活动、目标、判据、材料绑定、授权对象／判据范围与预算；使用配置时同步核 B3c 当前复用和策略用途门。现代授权 validity 必须 known.value.active=true，unknown／active=false 不能凭非空通过；既有 B0 prose 夹具仅保留明确开启的 legacy 读取兼容。写入仍受 CAS、幂等及依赖修订门禁。原授权不允许的对象或动作拒绝，控制后旧请求不能复活事件或父产物。重试回执不授权再次使用已删除／受限依据。此门禁不能阻止旧进程在宿主展示内容。

## 返回、收束与候选移交

每个结果标明 `synthetic_only: true` 与 `scoring: not_executed`。只读动作 `mutated: false`；检查返回 `ready/not_ready/needs_input/stopped/blocked/rejected` 或沿用保存组件的 `committed/conflict/not_saved` 等实际状态。`ready` 表示本用途在受控引用与声明下可继续，`committed` 表示逻辑操作已保存，幂等重放不产生新事件或新状态修订；均不是学习者达标。显式评估移交携带同一事件及材料上下文，接收方仍独立核授权、响应点、实际条件和采用。保存失败只返回失败回执，不返回未保存的 event_ref、事实条件或下一工作。

活动、目标和材料若明确携带 adoption，候选／重核／拒绝状态不能作为执行依据；full adopted 保留共享契约的非空声明范围及既有用途绑定，partially_adopted 须有覆盖当前活动、判据与用途的可检查范围。B0 导入的历史夹具没有 adoption 字段时继续兼容，不能将这点扩为真实采用权限。活动／分支额外 ObjectRef 参考核当前修订，可信历史事件／断点仍可按确切旧修订回查。

活动预定工作完成、预算结束、用户暂停、争议或当前路径无新信息时可保存收束。未完成要求只引用当前目标实际要求，未来必要时间条件未到可结束当前活动，目标外保持／迁移不创建欠账。没有合法父产物或可信事件时说明缺项，不从摘要还原原答。

同一缺口 `existing_need_ref` 只用于返回需求更新候选，不写入／采用需求。候选说明尚缺工作、必要理由、不做影响、条件与原答／帮助／父任务引用；收到候选不等于 AG1 接责或计划生效。需求处置、活动完成与正式目标支持保持分离，没有实际处理结果则待接收／待处理，不显示已安排。

参考疑误先限制相关用途，保留原答交 AG2；判据／目标和承诺问题交 AG1；合法非标准解、评分冲突与重要结论交评估责任方。原答足够时可请求直接重评，C0 不追加测验修复系统评分。材料、历史判断、实际误导和计划四恢复分别完成，本助手不解除专业限制或乐观覆盖旧判断。

保存冲突重读当前状态再决定，不循环替换期望修订；`not_saved` 保持事实待保存，不宣称跨会话可恢复。删除后的恢复只用剩余合法依据，不能从请求文件、旧 stdout 或摘要取回已删证据。本切片的控制范围是受控记录与串行调用；真实展示认证、停止旧执行者、自动接责与外部副本清理仍需宿主落实。
