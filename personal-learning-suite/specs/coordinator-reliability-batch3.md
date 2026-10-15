# Task & Artifact Coordinator：第三批并发与恢复接口

日期：2026-10-13。版本：tac-reliability/0.1.0，扩展第二批tac-workspace/0.1.0，不替代共享契约。

本批通过ReliableCoordinator提供有期限的依赖等待、同事务事件、采用指针前置条件、回执查询、旧工作区显式升级与只读恢复检查。底层仍使用SQLite短事务、全局state_revision冲突检测和operation_id幂等。没有新增Agent、自动专业采用或后台调度器。

## 等待具体结果

只在确实依赖某个新结果时使用policy=after_task；与修订无关的工作继续使用adopted或明确exact输入。请求必须指定已登记生产任务producer_task_id、对应稳定产物id、用途、范围和有限wait_timeout_ms。范围必须由上游生产任务覆盖，期限为1—86400000毫秒。

```json
{
  "operation_id": "register-dependent",
  "expected_state_revision": 12,
  "id": "dependent-M3",
  "assignee": "AG1",
  "task_kind": "production",
  "scope": ["M3"],
  "intended_use": "teaching",
  "output": {
    "id": "teaching-design-M3",
    "type": "ActivitySpec",
    "requires_ag3_review": true
  },
  "inputs": [
    {
      "id": "material",
      "policy": "after_task",
      "producer_task_id": "revise-material",
      "scope": ["M3"],
      "intended_use": "teaching"
    }
  ],
  "wait_timeout_ms": 300000
}
```

示例中的ID和状态号是占位说明，不是现有课程对象。实际请求须使用当前登记任务与查询取得的状态号。

assignee调用start时，若指定任务未提交，或其确切结果尚未按相应用途/范围采用，则登记waiting和持久化期限。重复start不延长期限。候选出现不自动放行；指定结果正式采用后，任务转回registered并提示assignee开始，随后锁定该确切结果，不偷偷换成任意最新版本。

上游failed/cancelled/blocked、结果被更新版取代或期限到达时，等待转blocked，并把下一责任交还requester。多层等待中的失败在同一提交中传播。程序不自动降级到旧版、不将blocked解释为学习者失败；恢复工作由AG0重新安排或明确创建新任务。

没有常驻宿主时，期限不会在无人调用程序的时刻自动发消息：status只读呈现effective_phase和refresh_needed；refresh或下一次写操作将已发生的过期落实为状态与事件。客户端应有限轮询并在关键节点检查。时间源默认是宿主epoch毫秒，测试可注入时间；期限机制依赖宿主时钟正确运行。

## 并发和指针条件

SQLite一次只有一个短写事务，生成、审查等专业工作不持有数据库锁。锁等待默认3秒，可返回busy/retryable，失败不提交；不是全局任务等待锁。独立事实登记可以在重新读取状态后有界重试，专业决定不得盲目换状态号重试。

adopt支持expected_pointers，每个拟改动的id/intended_use/scope都须列出预期旧revision；null表示此前没有指针。如果实际指针不同，返回pointer_conflict，即使调用方刷新全局state_revision也无法绕过原预期。

```json
{
  "expected_pointers": [
    {"id": "material", "intended_use": "teaching", "scope": "M3", "revision": 1}
  ]
}
```

该字段与原adopt请求合并使用，不能单独采用。为兼容第二批，未提供时仍执行全局CAS、版本/回执/依据检查；推荐AG0为真实采用明确携带指针条件。新判断需要明确更新预期，不把它伪装成原操作重试。

所有成员合格后，指针、整组记录、操作回执和本地事件在同一事务中提交。外部版本文件仍由调用方完整写入；登记和读取校验其指纹，没有宣称文件系统与数据库是一个跨介质事务。

## 本地事件

events(after_sequence, limit)按严格递增序号返回本地已提交事实，包括任务变化、候选、采用、wait_ready/wait_blocked等。未提交或回滚的事件不可见；同一operation_id重试不发第二次事件。无变化返回空列表，消费方保存next_sequence；可一次拉取1—1000条。

事件只包含必要协调定位，不复制专业正文。当前控制会过滤受暂停、删除或用途限制影响的事件；游标可以越过被过滤的历史行，不能通过旧事件恢复已删内容。过滤不等于删除清理，本批没有管理聊天上下文或文件删除范围。

这是本地拉取接口，未发送邮件、聊天消息或系统通知。正在推理的Agent不会因为事件落盘自动获得新上下文，宿主仍要在开始、候选提交、审查返回及最终采用处进行可靠检查。

## 退出、回执与恢复

提交前进程硬退出：SQLite在重新打开时处理未完成事务，旧采用指针保留，候选记录/事件不半发布。版本文件可能已由调用方写入但尚未登记，程序只报告这些文件，不自动采用或删除。

提交后返回丢失：operation(operation_id)可以查询已保存回执；同请求重试返回原回执，不增加状态号、产物版本或事件。not_committed仅表示当前一致快照未见该提交，不证明原执行者已经结束。commit_status_unknown明确区分“返回失败”与“确定没保存”；不能因为返回丢失就启动一个不同operation_id重复工作。

recover只检查SQLite完整性、已登记文件指纹/存在性、显式scan_roots下未登记文件，以及仍标记running的任务。它不推断进程存活、不自动把running改失败、不恢复专业正文、不自动解除用途限制、不自动重审或采用。文件缺失或篡改保持不可用，不能从内容指纹重建原件。扫描根不得越出工作区或进入.coordinator；有删除/用途限制时保守跳过未知文件扫描。

常见顺序：查operation回执→查recover/status→有依据地继续原任务或明确finish→补专业核验→重新检查采用。保留原operation_id及版本快照，新的专业决定使用新的明确请求。

## 旧工作区

第三批CLI默认使用ReliableCoordinator。没有扩展的第二批工作区仍可只读state，不自动修改；返回reliability_upgrade_required。写入前由AG0显式upgrade，请求仅含operation_id和expected_state_revision。

升级在事务中创建events/operation_contexts及扩展版本标记，保留原任务、产物、回执、指针及操作记录。中途退出可重试。旧操作没有新增的安全查询范围信息时，直接operation查询返回legacy_operation_requires_original_request；使用原完整请求执行幂等检查，而不是猜造当时的输入。

没有直接升级本次保存的第二批历史验收数据库；该数据库前后字节保持一致。可信操作员角色绑定和外部控制门禁沿用第二批，没有宿主模型身份认证或正式学习入口切换。

## 使用入口

完整验收，使用maintenance下不存在的新目录：

```powershell
python -B -X utf8 personal-learning-suite/scripts/check_coordinator_reliability.py --output-dir maintenance/coordinator-batch3-rerun
```

查看第三批演示事件：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_workspace.py --workspace maintenance/coordinator-batch3-20261013/wait-workspace --role AG0 events --after-sequence 0
```

检查等待失败后的状态及未登记文件：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_workspace.py --workspace maintenance/coordinator-batch3-20261013/wait-workspace --role AG0 recover --scan-root staging
```

真实文件模式还须携带--control-projection指向当前有效来源投影。正式课程使用前需另行明确宿主角色绑定、唯一指针维护方及入口接入；本批完成的是本地组件与隔离验证。
