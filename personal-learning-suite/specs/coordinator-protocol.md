# Task & Artifact Coordinator：完整文件协作协议

2026-10-13，tac-complete/0.1.0。在前三批基础上实现原方案的任务、版本、依赖、关键节点校验和人工文件宿主接入。没有LLM调度角色；AG0仍决定工作、专业取舍和采用。

日常工作先使用[简短指南](coordinator-agent-guide.md)及[Agent入口](../scripts/coordinate_agents.py)，需要完整依据、恢复或特殊审查时再查本协议。简化层复用以下门禁；明确意图生成冻结请求，程序在同一提交事务内核对冻结控制、正文及预期状态，不自动刷新专业决定。

## 状态的唯一维护方

共享字段及专业主责继续从[共享契约](../contracts/shared-contracts.md)读取。协调数据库`.coordinator/records.sqlite3`唯一维护**已登记集合**的任务、版本指纹、依赖快照、回执、采用指针、事件及消费游标。正文保存在原工作区的不可覆盖版本路径，数据库不复制完整专业正文或学习原答。

外部`state/control.md`仍维护实际用户控制，`state/current.md`维护实际学习状态，`plan/current.md`维护当前学习安排。协调器不生成另一份学习进度、控制状态或计划正文，不根据自己的任务完成倒写“学习已发生”。禁止将这些权威文件作为普通协调产物登记。产物的导航文件可以引用协调查询，但不能独立维护另一份可修改的采用清单。

真实模式使用`FileControlGate`读取显式控制投影；投影绑定实际控制来源的指纹。来源变化立即拒绝继续使用旧投影。AG0根据用户新控制刷新投影，程序不自行理解Markdown、授权或专业结论。角色由可信本地操作员声明，不是模型身份认证；同模型顺序兼任必须如实标明。

## 五种版本状态

| 状态 | 程序依据 | 使用方式 |
|---|---|---|
| Draft | 登记任务时事务内分配修订；尚未完整提交 | 可记录编辑路径、基版、拟改范围；不进入正式输入 |
| Candidate | 文件完整、非空、指纹及指定结构验证通过后提交 | 默认采用指针保持；exact输入需明确暂定条件 |
| Verified | 当前依据下适用的专业确认、必要AG3审查及结构检查满足要求 | 可明确指定使用；是否正式采用由AG0决定 |
| Adopted | AG0核对回执、依据及预期旧指针后采用 | 按用途和范围作为默认输入；出现新限制或依据变化仍须复核 |
| Superseded | 原范围被其他正式采用版本取代 | 保留追溯，仅明确指定的历史/暂定任务使用 |

状态按用途/范围判断。`scope_states`明确部分采用、部分核验或替换，不能由总体标签扩大使用范围。候选写入或较高修订号不会自动切换采用。取消草稿可以留下修订空位；并行修订按明确`base_ref`追溯变化，不能把数字相邻当成内容继承。

验证配置由AG0在任务`output.validation_profile`中明确：`file_integrity`检查非空与指纹；`utf8`另外检查编码；`contract_fields`读取共享契约的必需字段和身份，对JSON进行结构检查。字段检查不是完整嵌套Schema验证，也不证明专业正确。专业核验由owner和必要AG3回执承担，`requires_ag3_review`必须明确，不要求所有小文件审查。

## 输入、依赖及影响

每个输入明确稳定id、用途、上游范围及策略：

- `adopted`：开始时取该用途/范围的采用指针。
- `exact`：指定确切revision。若不是当前采用版，必须提供非空`provisional_conditions`，保留暂定条件，不把候选伪装正式输入。
- `after_task`：指定已登记的`producer_task_id`及有限`wait_timeout_ms`，只等该任务的确切正式采用结果。候选未采用不放行，失败/取消/阻塞/超时交回requester；不自动降级旧版。

任务开始固定实际字节指纹和直接/传递版本；修订任务另锁定`base_ref`原文。工作中不会悄悄换成最新输入。新任务复用已经局部复核的上游时，锁定被明确确认的新来源，同时保留`original_ref`与`inherited_recheck_id`；旧产物原依据不改写。下次相关变化仍会再次失效。

`planned_changed_scope`说明草稿拟改部分；提交的`changed_scope`说明实际改动。未知为null，保守按可能相关处理。程序只比较显式范围和依据，不自动推断语义依赖；范围声明及相容性属于专业判断。不同用途、范围不能未经声明混用；同一输入范围分属不同修订时拆成明确任务。

提交候选即返回`affected_downstream`并产生`candidate_warning`，提醒比较而不撤销旧采用版。正式采用后相关未处理依赖变成`recheck_required`。未知范围保守标记；无关范围照常工作。审查进行中出现新目标版本会产生`review_target_warning`，原审查目标不变。

`recheck`由产物owner提供确切old_ref/new_ref、用途、范围与明确相容理由。若结论需要改正文，则另建修订任务。AG3补核使用`base_receipt_id`、`directly_checked_scope`、`inherited_scope`、`compatibility_rationale`，区分实际新读与明确继承；旧意见不能直接套到新版。

## 四个必须调用程序的节点

任务对外只报告`running`、`submitted`、`blocked`及实际提交回执，不填写百分比。`running`表示正在执行且尚无提交结果；`submitted`必须能定位产物版本/路径/指纹或绑定版本的审查回执；`blocked`提供阻塞原因与下一责任人。登记待开始、等待期限、失败/取消等内部生命周期仍保留用于可靠处理和追溯；等待及停止原因在工作摘要中归入blocked。任务submitted不代表产物已被采用，产物五种版本状态继续独立维护。

1. **任务开始**：AG0登记职责、输出政策、输入策略和必要等待；执行者start，取得snapshot实际字节，并读取boundary。登记草稿不锁住其他专业工作。
2. **候选提交**：正文写到新版本路径，submit或publish验证并登记。程序检查输入变化、提供影响清单；受影响结果可以保存候选，但未经处理不能确认/采用。
3. **审查返回**：AG3先start锁定target_ref，再review回传确切版本/依据/范围。版本变化仍可保留旧版审查事实；若要用于新版本，则明确补核或重审。
4. **最终采用**：AG0读取brief/boundary/diff，明确所有members、适用回执及每项`expected_pointers`。程序核对全部成员后，在一个短事务中更新指针、整组记录、回执与事件；任何成员不合格均不采用。

写操作要求`operation_id`和`expected_state_revision`。成功同请求重试返回原回执；不同载荷复用同一operation_id拒绝。采用前置指针必填，刷新全局状态号不能掩盖原指针已经变化。主动回退版本须另给`rollback_rationale`及仍适用的核验。专业操作不盲目自动重试。

`publish`先读回/验证草稿，独占安装新版本，再提交索引。宿主允许时使用原子文件安装；受限Windows文件系统可使用独占完整写入，全部写完、刷新及校验之前不会登记为可读版本。数据库与文件不是跨介质事务。中断可能留下未登记完整/不完整文件，recover只报告，绝不自动采用或覆盖。

## 宿主状态与事件接入

新入口是[scripts/coordinate_preparation.py](../scripts/coordinate_preparation.py)，前几批`coordinate_workspace.py`保留为兼容检查入口。真实学习工作区已有`coordination/control.json`时，新入口自动绑定控制投影；缺投影不得以synthetic替代真实模式。

以项目根为工作目录：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_preparation.py --workspace learning/embodied-intelligence --role AG0 brief
python -B -X utf8 personal-learning-suite/scripts/coordinate_preparation.py --workspace learning/embodied-intelligence --role AG1 boundary --task-id YOUR_TASK
python -B -X utf8 personal-learning-suite/scripts/coordinate_preparation.py --workspace learning/embodied-intelligence --role AG1 snapshot --task-id YOUR_TASK
python -B -X utf8 personal-learning-suite/scripts/coordinate_preparation.py --workspace learning/embodied-intelligence --role AG0 inbox --consumer-id YOUR_HOST_CONTEXT
```

YOUR_*为说明占位符，不是实际课程任务。snapshot以base64返回确切正文；Python调用`read_snapshot`直接得到bytes。不能把返回的路径重新当可变latest读。brief只提供短行动表，state提供详细记录；diff提供实际文本差异、指纹与声明范围，不能代替专业判断。

`current --artifact-id ID --intended-use USE --scope SCOPE`从采用指针返回确切正文，不取最高修订；依据待复核或受控制限制时拒绝正式读取。`receipt --receipt-id ID`显示审查目标、指纹、依据签名、直接/继承范围及当前是否仍适用于该目标。state中的receipts、dependency_edges及impacts均为登记事实的查询视图，不是第二套可编辑状态。已登记但尚未开始的依赖也会获得候选预警，仍不提前锁定快照或自动等待。

宿主在上述四个节点以及等待恢复时读取inbox或events。消费方收到事件上下文后，使用`ack_events`显式确认`consumer_id/through_sequence`；游标按本地角色/上下文持久保存，确认本身不再发通知。无变化不产生重复影响事件，也不必反复解析全量文件。当前控制过滤事件，不能从删除后的事件恢复内容。

这已经是人工文件宿主的实际调用路径，不要求新增调度模型或后台服务。正在推理的模型不会自动收到磁盘更新；宿主必须调用工具，四个关键节点本身仍可靠校验。没有工具能力时明确报告无法完成协调提交，保留已采用版；不以“注意最新版”的自然语言替代门禁。未登记的普通学习原答/反馈仍走既有人工协议，不为了本组件复制档案或阻塞不相关学习。

## 历史登记与恢复

`bootstrap`只允许AG0对空索引一次显式登记真实原件。每项需稳定id、revision、契约type、用途/范围、路径、原件sha256、明确依赖及审查政策；按拓扑顺序登记。历史采用必须提供原采用记录的路径/指纹/唯一文本锚点和登记理由。历史兼容说明也须绑定原始声明证据。全部同事务成功或回滚。

程序验证证据确实存在且未变，不替代AG0对证据含义的判断。迁入的是已存在的采用/兼容事实，不生成新专业确认、独立审查、授课或学习者能力；历史审查原件及范围保留，不自动把原AG3旧版意见改成新版。

旧工作区可只读；AG0显式upgrade后保留原任务/指针/回执，补充版本历史和未完成任务的草稿修订。不能隐式升级历史验收数据库。查operation解决返回丢失；recover检查数据库完整性、文件指纹/缺失、显式目录下未登记文件与running任务，不猜执行者死亡、不自动修正文或采用、不删除原件。暂停/删除/用途门禁不等于文件和聊天上下文清理。
