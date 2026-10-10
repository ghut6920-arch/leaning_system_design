# B7 有限真实试用的只读验证接口

日期：2026-10-04；局部适配 `pl-pilot/0.1.0`；共用对象继续由 [共享契约](shared-contracts.md) 唯一维护。依据 N00 第十二、十四节，D10 第十一、十二节，D11 第二至九、十一节。

## 本切片的行为与边界

B7 第一切片提供标准库 `PilotService` 的 `preflight` 和 `report`：对调用者提供的完整共享对象、原件及当前控制输入作只读核查，生成有限配置缺项和 V1—V4 引用审查结果。它不创建学习工作区、个人档案或第二套实验画像，不修改共享对象，不调用模型，也不执行学习、采用专业结论或安排后续任务。

真实试用尚未开始。真实记录的结构与出处声明可以提交核查；这些声明不构成身份认证、学科核验、实际显示确认或真实执行授权。本切片保持 B1—B6 的 `synthetic_only` 和 fixture 绑定限制，不把 `verified_for_fixture` 转为 `host_verified`，不开放真实记录写入。

模板 [b7-pilot-input.json](../templates/b7-pilot-input.json) 明确未配置；空列表和空原件映射只是尚无输入，不能推断没有帮助、没有接触、零成本或课程已完成。

## 请求

| 字段 | 含义 |
|---|---|
| `pilot_version` | 必须为 `pl-pilot/0.1.0` |
| `data_kind` | `unconfigured`、`synthetic` 或 `real`；真实模式不得借虚构 ID、原件或授权冒充真实依据 |
| `objects` | 完整 canonical 共享对象数组；包含所引用的具体修订及必要依赖，沿用 `type/id/revision/owner/schema_version/basis_refs` |
| `artifacts` | 安全逻辑相对路径 → 原件字符串的映射，仅在输入内存中核对 `ArtifactRef` 的原件及定位；不按该逻辑路径读取磁盘，输出不回显题面、原答、教师参考或个人摘要 |
| `instance_ref` | 当前 `LearningInstance` 的具体 `{id, revision}`；未配置为 `null` |
| `current_goal_refs` | 当前有限范围的 `GoalSpec` 具体修订引用；不自动选择设计案例或虚构目标 |
| `budget_ref` | 唯一共享 `BudgetEnvelope` 引用；未配置为 `null` |
| `validation_refs` | 需审查的 canonical `ValidationDecision` 引用，不另造四类结果对象 |
| `controls` | `known` 为布尔值，`deleted_ids/paused_ids` 为字符串数组；`restrictions` 项为 `{scope_id, intended_uses: [用途字符串]}`，`*` 覆盖全部用途；未知控制不能当不存在限制 |
| `followup` | `status` 为 `unknown/not_required/required`；另有 `goal_refs/purpose`，`required` 必须指向当前已就绪目标并说明真实用途 |
| `comparison` | `status/question/decision_needed/arms`；默认 `not_requested`，比较非首期启动的固定前置 |
| `host` | `mode/execution_available`；本切片为 `manual_single_entry`、`false`，没有实时执行通道 |

所有 ObjectRef 均指向明确修订。`Fact` 的未知、不适用、未执行继续按共享契约表示；缺字段和 null 不补造为 known。传入的对象只读结构检查使用共享定义，局部接口不复制一份手写必备字段表。

ObjectRef 带 `locator` 时也须实际定位：`requirements/<requirement_id>` 必须对应 GoalSpec 中存在的要求；其他定位目前只接受对象中已存在的直接字段。不存在的要求或未支持的嵌套路径不能仅因对象 ID 有效而通过。

`real` 要求真实课程与用途、预算/约束、独立于套件的用户选定记录根目录、可控记录范围和相应依赖有诚实来源声明；拒绝把 `FIX-*`、`synthetic_fixture` 或 fixture 绑定作为真实来源。通过此检查仅说明声明没有命中已知虚构标记，不能证明事实真实或承担者确有能力。缺失可靠参考、当前用途授权或可控保存条件时，输出缺项及可继续整理的范围，不承诺开跑。

`LearningInstance.course/purpose/user_constraints/record_root/actor_bindings` 使用 `Fact`。`actor_bindings` 的 known value 为 `AG0`—`AG3` 到非空承担者说明或 known Fact 的映射，允许同一承担者兼任相容角色；角色名仍不认证身份。`scope/record_control_scope` 接受 known Fact 或现有非空直接说明。`record_root` 声明须为绝对路径且在套件之外；工具不在该路径创建文件。

当前目标每个 requirement 的 `teaching_scope` 须说明 `whole_required`。为 true 时，还需 `whole_obligations` 和当前 SourceFragment/MaterialUse 中已声明支持的 `verification.content.whole_coverage`，含目标/判据具体定位、关键操作、整体义务与核验锚点。为 false 时不追加整体任务。来源核验可使用 B2b 的 `verification.content` 结构，或 known Fact 的 `{recorded_status, method, scope}`；`supported_for_fixture` 仅适用于 synthetic。它们都是可核查的声明格式，不是本工具重新做了学科核验。

整体覆盖声明还须建立在当前内容核验支持之上；MaterialUse 的当前用途核验也须支持且绑定当前修订。单独填入 whole_coverage 的支持标签不能覆盖 `pending_review`、未知或过期的内容/用途状态。

`BudgetEnvelope` 的四个轴须明确 known 或附理由的 `not_required`，授权还要覆盖当前目标、同一预算、`planning/budget_allocation` 决定及 active validity。synthetic 保留 `verified_for_fixture`，real 只能提供 `host_verified` 声明，B7 不签发该绑定或授权。费用无法确定时保持 unknown，配置据此保持相应缺项；报告不以 0 替代。

## 验证记录沿用唯一共享对象

验证输入使用既有 `ValidationDecision`：`validation_layer/case_id/host/versions/executor/checker/raw_output_ref/status/limitations/cost/decision/replay_of` 不在 B7 改名或重复维护。`validation_layer` 分别写 V1、V2、V3、V4，不汇总成一个系统效果分数。

针对有限试用的引用索引放在该对象 `metadata.pilot` 中：

```json
{
  "goal_refs": [],
  "event_refs": [],
  "judgment_refs": [],
  "claim": "current_support"
}
```

这是字段形状片段，不是可通过的验证记录；需填入已存在的合法引用和 canonical 字段。`claim` 使用固定枚举，限定陈述及专业解释仍写原对象 `decision/limitations`：

| 层 | `metadata.pilot.claim` | 本切片的必要输入 |
|---|---|---|
| V1 | `configuration` | 非空当前 `goal_refs`，当前要求/内容来源及其已声明核验；只核配置引用 |
| V2 | `software_behavior` | 当前 `goal_refs`、非空 `event_refs`、可定位原答和含 `initial_response` 的 timeline；只核行为记录引用 |
| V3 | `current_support/learning_gain/retention/design_effect` | 当前目标、事件、非空 `judgment_refs`；Judgment 当前修订、已采用、双轴与实际条件可查，所引事件和目标在同一声明范围 |
| V4 | `collaboration_gain` | 当前目标及下表完整比较声明，两个以上不同活动/样本和四轴成本 |

V3 的 `learning_gain/retention` 还需要非空 `baseline_event_refs`、`baseline_judgment_refs` 和 `baseline_comparable={"status":"known","value":true}`。基线判断须为当前修订、已采用、`eligibility=usable`、支持轴已知，且条件、事件和当前判据可比；只有当前答对而基线未知不能证明增益。`learning_gain` 至少需要同一可比要求的 `observed_not_met` 基线与 `supported/usable` 当前判断。基线与当前事件须不同 ID、不同 `independent_sample_id`，原答的 path/revision/locator 身份也须不同；更换事件和样本 ID 不能把同一原件变成独立样本。基线控制和原件同样可用；声明可比不证明实际等难。`design_effect` 在本切片不能确立归因；仅当其他引用及条件全部可用时，保留范围为 `current_support`，附 `design_attribution_not_established`，不自动将学习变化归因于教学设计。

`retention` 还核目标 `time_requirements` known value 的 `{minimum_delay_seconds, requirement_ids, require_no_contact}`，后者须为布尔值。沿用 [B3a 时间约定](assessment-b3a.md)：`contact_history` known value 为 `{last_relevant_at: 带时区ISO时间或Fact, intervening_contact: Fact}`；严格无接触要求下 `intervening_contact` 须 known false，实际显示的相关帮助/练习/反馈仍计接触。

采用的 Judgment `conditions.response_points` 项为 `{event_ref, sequence}`，必须指向原事件具体响应点，该响应点 `time` 需 known 且有带时区时间；未知修订时间不回退到初答时间。父事件或继承接触尚未核清时保持限制。没有正式保持要求或实际合格时窗，不填保持通过。

上述数组是对象引用，原答、帮助、实际接触及成本仍维护在原 canonical 对象与原件中。不能用 metadata 复制个人原答或补造未发生的过程。`ArtifactRef` 当前只读核查接受 `revision=1`、非空 origin、逻辑相对 path 与原件中实际存在的 locator 字符串；更复杂原件修订/定位能力尚未绑定。

| 层 | 必须能回查的内容 | 报告保留的限制 |
|---|---|---|
| V1 内容与评价 | 当前目标/判据、活动及材料用途、关键参考及其核验、原答及相应判断 | 结构/引用有效不证明学科正确；未核版本和用途不计可靠覆盖 |
| V2 教学过程 | 原任务、原答、帮助时序及替代操作、下一步依据、父产物/停止/恢复条件 | 原事件不足就保持待查；流程标签和顺畅摘要不证明关键工作由用户完成 |
| V3 目标条件下表现 | 合格事件、Judgment 双轴及采用状态、允许资源、时间/接触条件；需要时可比起点 | 同题修订与同一样本不增加独立证据；无可比起点只能取得当前支持；延迟仅按真实要求及实际条件 |
| V4 协作增量 | 预先声明的具体比较、合格简化路径与新增做法、质量、完整成本与偏离 | 无比较保持未知；角色数/调用量不算增益；不把未执行工作算节省完成同目标的成本 |

`ValidationDecision.status` 接受 `passed/failed/not_executed/unknown/not_required`；passed/failed 需非空 `executor/checker/host/versions` 和可定位的 `raw_output_ref`，passed 另查相应层引用与限定 claim。它仍是原记录声明，不是程序自动给学习者评分。

成本使用 canonical `BudgetEnvelope` 四轴或 `ValidationDecision.cost` 四轴，不另建成本对象：`user_active_time/blocked_wait/system_effort/fees` 各为 Fact。known value 接受非负有限数值，或只有一个数量字段的对象；数量字段为 `amount/minutes/seconds/units/tokens/value/calls`，`amount/value` 可以注明 `unit=minutes/seconds/tokens/calls/units/USD/CNY`。对象可注明 `measurement` 或 `kind`：`observed/measured/recorded/actual` 输出为 observed，`estimated/estimate/manual_estimate` 为 estimated，`user_limit/synthetic_limit/limit/budget_limit` 为 limit，缺失则为 unknown；不把额度当实际耗时。

例如未测费用为 `{"status":"unknown","reason":"尚无可核对费用"}`；不适用须附 `not_required` 原因，不能把缺测改为不需要。估计/观测来源与细分说明仍放 canonical 原记录及 accounting notes，本工具不认证数值来源。

主动投入、阻塞等待、系统准备/核验/维护、费用分别解释。unknown 不当零，估计不当观测，同会话内细分不重复相加，首次构建与复用区分。报告按原记录输出成本，不自动加总四轴或多个验证记录，不能自动测量时间、费用或用户负担。

## 比较的具体局部形状

V4 优先读取 `ValidationDecision.metadata.pilot.comparison`，未提供才读取顶层 `comparison`。默认 `not_requested` 不阻塞普通准备；若要报告 `collaboration_gain`，本地形状如下：

| 比较字段 | 当前要求 |
|---|---|
| `status` | `requested` |
| `question/decision_needed` | 非空说明或 known Fact，先说明哪项分工及取舍问题 |
| `planned/comparable` | `{"status":"known","value":true}`，声明比较事先规划及条件可比 |
| `matching_basis` 或 `matching_basis_refs` | 非空 known Fact 说明关键操作、产物、前置、材料及暴露匹配依据；或非空且可解析的 canonical 引用数组；所声明引用须为当前修订并经过删除、暂停和用途限制检查，顶层比较同样适用 |
| `arms` | 至少两项，分别指向不同 ID 的 ActivitySpec，并用不同 PerformanceEvent 样本；不同修订的同一活动也不能制造独立单元 |
| 每项 `unit_ref` | ActivitySpec 的 `{id, revision}` |
| 每项 `prior_learning` | `{"status":"known","value":"unlearned"}` 或 value=`not_previously_learned`；保留尚未学过的真实依据 |
| 每项 `event_refs` | 非空 PerformanceEvent 引用数组，原答必须存在且可定位，activity_ref 匹配本 arm，活动与当前 goal_refs 相关，跨 arms 不复用同一样本或同一原答原件；改活动 ID 也不能把同内容任务算成不同单元 |
| 每项 `conditions/quality` | 非空 known Fact，分别记录实际条件与必要质量；不是直接空字符串或自报难度标签 |
| 每项 `cost` | 上述四轴 Fact，各轴 known 或有实际原因的 `not_required`；unknown 导致完整比较成本未就绪 |

这只是已声明的比较条件和出处核查。工具不会确认单元真的尚未学过、自动随机分组、认证质量相当或估计因果效应；输入不能回答这些问题时保留限制。真实帮助照常提供并记录，不能为了实验形式拒绝教学。

## 控制、依赖与报告

核查先识别删除、暂停、限制，再核对象和修订依赖。已删依据、过期目标、不完整原件定位、未知必要控制或缺失依赖，均不能因存在一份旧“通过”记录而恢复当前用途。判断部分仍有效时限定合法剩余范围；验证工具不替 AG3 重评或自动补测。

受限验证记录不输出其判断摘要或成本数值，成本轴保留 unknown；无关且仍有效的层可继续独立报告。该行为仅限制本次输出，不宣称擦除了调用方已保存的副本。

`preflight` 检查当前有限配置及未覆盖项，返回 `prepared/needs_input/rejected`。`prepared` 只表示输入准备检查的有限结果，`inputs_ready` 不开放实时执行。复杂整体参考、目标内后续条件尚未就绪，可以报告可靠子范围，但不能将浅目标结果泛化到深目标或宣布完整首期闭环结束。用户预算、用途和记录目录未提供时保持未配置。

`report` 顶层返回 `reported/needs_input/rejected`，V1—V4 各自 `reported_status` 为 `passed/failed/not_executed/unknown/not_required`；没有记录的层保持 not_executed。`reported` 只说明这次审查返回，不表示四层通过。不能仅据 canonical `status` 自报 passed 就宣布效果已证实。响应包含 `reviews.V1`—`reviews.V4`，各自保留 `reported_status/review_refs/reasons/claim_scope/assessments`；synthetic 的 `real_results` 始终 not_executed。`costs` 不生成总体评分。输出仅包含元数据、引用、缺项及限制，不回显原答正文，也不构建持久化报告缓存。

通用输出含 `pilot_version/data_kind/status/reasons/inputs_ready/can_start_automated/live_execution_status`。`reasons` 只给代码和引用，不嵌入个人原文；`can_start_automated=false`、`live_execution_status=not_enabled` 明确本切片无真实执行能力。

删除控制只作用于本次报告是否继续使用输入中的依据。本切片没有清理外部 JSON、调用者已存原件、stdout、导出或聊天历史的能力；这些文件不进入既有 SQLite 的删除控制范围。包含个人输入的请求与报告必须在用户实际选择的可控范围维护。删除关联验证索引后，不应从旧请求或旧报告重新导入已删内容。

## 调用与验收

`PilotService()` 无需构造参数，提供 `preflight(request: dict) -> dict`、`report(request: dict) -> dict`。项目根的主入口不需要 `--workspace`：

```powershell
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action preflight --request personal-learning-suite/templates/b7-pilot-input.json
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action report --request personal-learning-suite/templates/b7-pilot-input.json
```

独立模块在 `personal-learning-suite/src` 工作目录运行：

```powershell
python -X utf8 -m runtime.pilot_b7 preflight --request ../templates/b7-pilot-input.json
python -X utf8 -m runtime.pilot_b7 report --request ../templates/b7-pilot-input.json
```

命令读取结构化请求并向 stdout 输出元数据。独立模块 CLI 退出码 `0` 表示 `prepared/reported`，`2` 表示 `needs_input`，`1` 表示 `rejected`；主入口 CLI `rejected` 为 1，其余可返回结果为 0，应同时读取响应 status 和四层状态。未配置模板 preflight 为 needs_input、report 为 reported 且四层 not_executed，这些是正常未就绪/未执行结果，不是通过。实现见 [pilot_b7.py](../src/runtime/pilot_b7.py)，验收见 [B7 有限验收](../specs/b7-acceptance.md)。

受控虚构用例只验证配置核查、引用约束及保守报告行为，不构成真实课程 V1—V4。[B10 覆盖脚本](../scripts/check_b7_coverage.py) 读取实际报告及原始输出，生成 `validation/b7-b10-coverage.json`，列出十二个情境的软件切片与未覆盖面；所有 `full_scenario_status` 保持 `not_executed`，不改 B0 历史情境。软件切片通过不能自动升级为完整 B10 已验证。
