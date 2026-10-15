# Task & Artifact Coordinator：第二批文件接口

版本：tac-workspace/0.1.0。日期：2026-10-13。

本批提供任务登记、开始时的输入快照、候选提交、专业确认、AG3版本审查、局部输入复核及AG0整组采用。专业正文留在工作区原版本文件中；.coordinator/records.sqlite3只维护协调元数据和回执，不复制专业正文或学习者原答。

## 权威来源和职责

对象类型与专业主责由[共享契约](../contracts/shared-contracts.md)的唯一JSON定义读取，不另维护第二份所有者表。首版仅支持GoalSpec、SourceFragment、MaterialUse、ActivitySpec、MethodConfig、PlanCommitment的文件版本索引；保守使用契约列出的首位专业主责，没有推断AG0的可选委派。

协调记录是WorkOrder/WorkResult等语义的局部视图，不是已通过完整共享对象验证的学习记录。程序不评价学科正确性、教学充分性或学习能力。专业角色明确确认，AG0依据这些回执收口交付集合；角色名本身不证明身份。

可信本地操作员通过bind_local_operator创建角色会话。CLI的--role也是操作员声明，不能由不可信Agent自由选择后当成鉴权。请求正文不接受actor/role/owner/binding_status顶层字段，代码不写host_verified。本批没有宿主模型身份绑定、恶意共享文件系统隔离或操作系统权限隔离。

.coordinator中的采用指针只管理显式登记的文件集合。既有学习state/control/current、plan、Agent/Skill与旧运行器没有改由它维护；真实学习部署前仍须决定字段唯一维护方和入口接入。旧版active清单不自动导入为正式采用。

## 操作

所有写操作携带operation_id和expected_state_revision；角色来自绑定会话。成功操作重试返回原回执，不重复登记。不同载荷复用同一operation_id拒绝；全局状态冲突不提交，调用方重新读取状态后检查再重试。

| 操作 | 主要输入 | 行为 |
|---|---|---|
| register | id、assignee、task_kind、scope、intended_use；生产任务的output/inputs或审查target_ref | 建立registered任务。AG0明确生产产物的AG3审查要求 |
| start | task_id | assignee接责，按输入策略锁定确切版本、用途、范围和指纹 |
| submit | task_id、path、changed_scope | 验证新版本路径、非空文件、指纹与输入变化，登记candidate；不更新采用指针 |
| confirm | ref、receipt_id、scope、intended_use、outcome、rationale | 专业主责确认；绑定正文指纹与全部有效依据签名 |
| review | task_id、receipt_id、scope、intended_use、outcome、rationale | AG3记录开始时锁定目标与依据的意见，不跟随最新写入文件 |
| recheck | ref、recheck_id、old_ref、new_ref、scope、intended_use、rationale | 产物专业主责对当前实际发生的上游变化显式声明局部相容；原依据不改写 |
| adopt | bundle_id、members | AG0核对版本、依据、用途、范围、主责确认及必要AG3覆盖，再一次更新全部指针 |
| finish | task_id、phase、reason | requester或assignee登记failed/cancelled；保留已采用旧版 |

intended_use每个版本明确声明一个用途；跨用途不自动转用，可通过独立MaterialUse对象表达。scope使用非空稳定范围标记。不同范围若已采用不同修订，调用方拆成明确任务，程序不猜如何混合使用。

inputs中每项为{id, policy, scope, intended_use}。policy=adopted在start时取该用途/范围的正式指针；policy=exact另外携带revision，表示显式指定版本，可以暂定使用候选。任务创建或草稿存在不阻止其他任务使用旧采用版。指定采用输入尚不存在时返回adopted_input_unavailable，不无限等待。

changed_scope为明确范围列表或null；null表示未知，按可能相关处理。已声明不相交的变化允许任务继续，但该声明是专业方提供的范围信息，不是程序对语义无影响的证明。basis_refs沿输入版本的已有引用展开；未声明的语义依赖不会被程序自动发现。

## 快照与审查

read_snapshot返回锁定版本的实际字节，读取前后校验控制与指纹，不用可变latest路径重新读取。源文件被外部覆盖时拒绝，不能靠索引哈希恢复原文。新修订必须新路径；这个约束由协调接口和读取校验落实，不是磁盘写保护。

任务快照不会随指针更新。受影响输出可以保存candidate，但必须完成局部输入复核或另建任务更新产物，然后重新取得适用于当前依据签名的专业确认/审查。recheck绑定确切旧版、新采用版和范围；下一次相关上游更新会使它重新失效。新来源的上游引用也继续纳入检查，不在局部复核处断开依赖链。

AG3可全量审查，也可提供base_receipt_id、directly_checked_scope、inherited_scope、compatibility_rationale。程序要求继承范围被原支持意见覆盖，原版与新版属于同一稳定产物，检查与继承范围无交叉且合计等于本次覆盖范围。是否相容由AG3明确判断；程序不把继承范围记成直接重新阅读。输入局部复核引用的新版本会同时提供给AG3读取，原历史依据仍保留。

意见的supported/partial/rejected是专业声明，不是程序评分。同一目标、用途、依据和范围存在未处置的非支持意见时阻止相关使用和采用。相应专业方可在新回执中通过supersedes_receipt_ids及明确理由处置自己的旧意见；不能替代其他专业方的结论，也不按最后到达自动消除冲突。

## 整组采用

采用检查以members组成的拟采用集合为基准，包括同组的新上游候选。暂定依据的专业确认须显式allow_provisional=true；单独采用下游仍会因输入未采用而失败。整组只有所有成员、范围、确切回执和必要审查均合格，才一次写入指针；任何一项不合格都不更新其他成员。

采用和核验状态保存在独立回执，正文版本及其指纹不因通过审查而变化。status的adoption字段由用途/范围指针生成，不修改版本原记录。当前仍使用保守的全局state_revision冲突检测，第三批再验证并发和恢复；没有宣称文件写入与SQLite是跨介质原子事务。

## 外部控制

real_file_metadata模式必须提供外部control_gate；未绑定时不能初始化或操作。宿主可以提供回调，CLI可以读取人工确认的控制投影。投影明确包含state_revision、paused_ids、deleted_ids、restrictions和source_refs；每个source_ref将实际控制来源路径绑定sha256。程序不自行解释Markdown中的授权或暂停含义。

来源文件变化时投影失效，必须重新依据真实来源生成；不能独立编辑投影后冒称当前来源状态。所有关键写入及重试都先检查控制，提交前重读控制。删除先于正文读取；限制不因提交新版而自动解除。暂停、用途限制与删除门禁不等于实际文件/历史清理，本批没有实现删除清理或宿主上下文撤回。

synthetic_demo模式可以不提供外部控制，仅用于明确虚构的隔离演示。现有真实课程没有初始化为该模式。

## 使用

从项目根执行隔离演示和完整验收，输出目录须是maintenance下不存在的新目录：

```powershell
python -B -X utf8 personal-learning-suite/scripts/check_coordinator_workspace.py --output-dir maintenance/coordinator-batch2-rerun
```

查看本次演示的本地状态：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_workspace.py --workspace maintenance/coordinator-batch2-20261013/demo-workspace --role AG0 state
```

单次写操作从JSON请求文件读取，操作员声明相应角色：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_workspace.py --workspace YOUR_WORKSPACE --role AG2 execute --action submit --request-file YOUR_REQUEST.json
```

上述YOUR_*为使用说明中的占位符。完整实际请求可看本次[演示轨迹](../../maintenance/coordinator-batch2-20261013/scenario.json)或[跨进程CLI请求](../../maintenance/coordinator-batch2-20261013/cli-transcript.json)。拒绝会返回具体原因，未自动执行专业回修、派发Agent、重试采用或建立全局等待锁。
