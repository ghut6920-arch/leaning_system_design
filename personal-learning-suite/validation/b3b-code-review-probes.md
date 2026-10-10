# B3b 独立代码复核：人工探测原始观察

日期：2026-10-03。全部探测为 `synthetic_only` 人工夹具，使用 Python 标准库临时目录中的独立 LearningStore；未运行模型或外部服务，未修改 runtime、原夹具、请求文档及已通过的语义前向输出。临时目录已清理。

只读范围：`src/runtime/learning_teaching.py`、`learning_store.py` 的公开接口及相关事务实现、`contracts/runtime-b1.md`、`contracts/teaching-b3b.md`、Skill 的运行引用。经主代理指定，只读取 `tests/test_b3b_teaching.py` 第 1—99 行的 constants／anchor／fixture／initial_request，以及 `tests/test_b2b_materials.py` 第 1—115 行的构造 helpers；没有读取测试方法、断言或已有验证结论。fixture() 调用自身所需的基线原件是人工输入，不是验证预期。

本报告保留修复前的实际观察。runtimeworker 在复核期间并行修改预算及父任务继承；本报告不把当时结果当作修复后的状态，也未自行修改源文件。主代理已接收前三项以安排修复与定向复验。

## 公共复现设置

每项都新建独立临时目录，以 `LearningStore(temp_root, entry_actor="AG0")` 初始化，调用 `fixture()` 得到 snapshot、artifacts、context，再通过公开 `store.import_fixture(snapshot, artifacts)` 导入，回执 `committed/state_revision=1`。以 `TeachingService(store)` 执行请求；`initial_request()` 使用 `FIX-activity revision 1`、`FIX-b3b-teaching-grant revision 1` 和 fixture 的精确 context。读回通过 `read_refs`，没有直接绕过存储读取 SQLite。

## 1. 已知更早发生的帮助仍排序在初答之后

位置：`TeachingService._append` 通过 `event["timeline"][-1]["sequence"] + 1` 排序；`_timeline_entry` 只检查 time 是 Fact，没有比较已知发生顺序。

触发：

1. 将 initial_request 的 `initial_response.time` 设为 `{status: "known", value: "2026-10-03T09:00:00+08:00"}`；记录初答成功。
2. 对返回的当前 event_ref 调用 `record_help`，使用当前 CAS、新 operation_id、合法 fixture 授权。
3. help 为 `visibility: "displayed"`，代做 `connect-P-to-Q`，time 明确为 `{status: "known", value: "2026-10-03T08:59:00+08:00"}`。

实际 `record_help` 回执：`status: committed`。公开 API 读回的关键持久字段如下：

```json
[
  {"kind": "initial_response", "sequence": 1,
   "time": {"status": "known", "value": "2026-10-03T09:00:00+08:00"},
   "visibility": "displayed"},
  {"kind": "help", "sequence": 2,
   "time": {"status": "known", "value": "2026-10-03T08:59:00+08:00"},
   "visibility": "displayed", "substituted_operations": ["connect-P-to-Q"]}
]
```

结果：持久 sequence 与声明的发生时间相反，服务既未拒绝不相容声明，也未将其标为迟到补记／顺序未决。按 sequence 消费的评价方会把初答看成该帮助之前。此探测只说明时间线一致性缺口，不证明人类夹具的真实时间。

## 2. 提交失败仍返回未保存事件条件和下一教学工作

位置：`TeachingService._commit` 取得真实 store 回执后无条件 `response.update(extra)`；extra 由候选 event／checkpoint 在事务之前生成。

触发 A：fresh fixture 的状态为 1，但调用 `initial_request(state_revision=0, operation_id="FIX-probe-CAS")`。

实际返回选段：

```json
{
  "status": "conflict",
  "state_revision": 1,
  "mutated": false,
  "event_ref": {"id": "FIX-b3b-event", "revision": 1},
  "factual_conditions": {
    "displayed_help": {"status": "known", "value": []},
    "unknown_visibility": false,
    "independent_support": "not_assessed"
  }
}
```

随后 `store.read_refs([返回的event_ref], "read")` 为 `rejected`，原因 `missing_reference`：该 revision 1 未保存。

触发 B：fresh fixture 中正常记录初答，使状态变为 2。随后合法构造 `record_feedback`，对当前初答 event_ref 引用 branch_index 0、原答 ArtifactRef 和可定位 quote；反馈为 displayed，但故意给旧 `expected_state_revision=1`。

实际返回选段：

```json
{
  "status": "conflict",
  "state_revision": 2,
  "mutated": false,
  "event_ref": {"id": "FIX-b3b-event", "revision": 2},
  "factual_conditions": {
    "displayed_help": {"status": "known", "value": [
      {"sequence": 2, "kind": "feedback",
       "target_operations": ["connect-P-to-Q"],
       "substituted_operations": ["connect-P-to-Q"]}
    ]},
    "substituted_operations": ["connect-P-to-Q"],
    "independent_support": "not_assessed"
  },
  "learner_next_work": "在同一题原有事件中写出 P 与 P→Q 的连接理由"
}
```

`read_refs` 对返回的 event revision 2 再次明确 `missing_reference`。回执的顶层 conflict／mutated=false 如实表示失败；问题是同一个失败回执仍携带未保存且未标 candidate／pending-save 的事件条件，以及可被宿主直接展示的下一教学工作。没有观测到 store 错误提交或回执误报 committed。

## 3. 明确未采用的活动候选可成为新执行依据

位置：`TeachingService._prepare` 检查当前对象修订与任务资格声明，但未检查活动的显式 adoption 状态。

触发：在导入前，只向 fixture 的 `FIX-activity revision 1` 增加以下元数据，其他活动、材料、授权均保留：

```json
{
  "adoption": {
    "status": "candidate",
    "by": "AG1",
    "basis_refs": [{"id": "FIX-goal", "revision": 1}],
    "scope": "draft fixture activity",
    "limitations": ["not adopted"],
    "time": {"status": "unknown", "reason": "no adoption happened"}
  }
}
```

通过公开 import_fixture 导入成功。随后 open 与 record_initial 的实际返回：

```json
{
  "open": {"status": "ready", "reasons": []},
  "record_initial": {
    "status": "committed", "mutated": true, "reasons": [],
    "event_ref": {"id": "FIX-b3b-event", "revision": 1}
  }
}
```

读回新 PerformanceEvent 的 `activity_ref` 是 `{id: "FIX-activity", revision: 1}`。明确标为 candidate 的活动已成为持久新事件的执行依据；没有采用回执或后续状态变化。本探测实际只改 ActivitySpec；没有把未探测的 GoalSpec／MaterialUse 情况当作已复现。

## 4. 额外活动参考的旧修订仍可支持新执行

这是额外明确观察，已报告主代理；是否要求“旧但合法的内容修订”一律拒绝，应由当前版本兼容政策判定。不能把正常历史读取等同于错误，也没有观测到绕过删除控制。

触发：

1. 从 fixture 的 SourceFragment 复制一个独立 `FIX-only-reference revision 1`，导入前令活动的 `reference_refs` 和 branch 0 的 `reference_refs` 都只引用该对象；它不加入 MaterialUse 的 fragment_refs，原材料来源保持不变。
2. 导入后以 `LearningStore(temp_root, entry_actor="AG2").commit`、合法 `FIX-b2b-material-grant revision 1`、`FIX-b2b-material-work revision 1` 将该 SourceFragment 推进到 revision 2，更新其 claims 和 verification.checked_revision。实际 source revision 提交成功，状态为 2。
3. 活动仍精确引用该独立参考 revision 1；调用 open 与当前 CAS 的 record_initial。

实际返回：

```json
{
  "reference_revision_commit": {"status": "committed", "state_revision": 2},
  "activity_reference_refs": [{"id": "FIX-only-reference", "revision": 1}],
  "open": {"status": "ready", "reasons": []},
  "record_initial": {"status": "committed", "mutated": true, "reasons": []}
}
```

对应位置是 `_prepare`／反馈分支对 reference_refs 使用 `_guard`；公开 validate_refs 允许确切合法历史引用，没有替服务检查最新修订。此处新执行没有显式版本兼容说明，却沿用额外旧参考。

作为范围对照，另一个独立临时夹具中，直接把 MaterialUse 已引用的 `FIX-content-source` 推进到 revision 2 后，open 和 record_initial 都返回 `blocked/stale_basis_reference`。因此额外观察限定为 ActivitySpec／branch 的独立参考，不是所有来源修订均失守。

## 边界与后续

没有把合法旧 checkpoint／旧事件的历史读取列为缺陷：历史原答可以按具体修订读取，且恢复条件仍保留未记录帮助未知。没有证据说明已删内容被复活，未声称此方面全面验证通过。

以公开 API 修订 AuthorizationGrant 的尝试受 bootstrap 单对象修订门及授权创建限制阻止，因此“旧授权修订仍可执行”没有形成有效运行复现，不列为发现。

主代理已安排前三类修复；建议修后仅重跑这些触发，核实逆序帮助被明确拒绝或保留正确发生顺序，失败回执只保留真实已保存引用／明确待保存候选且不发下一工作，明确 candidate 活动不能作为新执行依据。第四项只保留原始观察，待版本兼容政策确认；本报告没有自行扩大修复范围。
