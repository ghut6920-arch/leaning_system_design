# B3b 运行接口与边界

本说明记录 B3b／B4 开发程序的调用与限制；SK03 的专业教学规则也可用于合法的人工文件学习，但本程序仍只接受虚构记录。共享字段唯一维护源为 [共享契约](../../../../contracts/shared-contracts.md)；保存与控制承载沿用 [B1](../../../../contracts/runtime-b1.md)，C0 请求见 [teaching-b3b.md](../../../../contracts/teaching-b3b.md)。助手在 [learning_teaching.py](../../../runtime/learning_teaching.py)，使用同一 `records.sqlite3`；[AG0](../../../agents/AG0-coach.md)的角色说明不授予真实宿主技术权限。

## 实际调用

调用 `TeachingService(store).run(request)`；CLI 请求为 UTF-8 JSON 文件，action 写在载荷中：

```text
python personal-learning-suite/src/runtime/learning_teaching.py --workspace <虚构开发记录目录> --request <C0请求.json>
```

只处理 `synthetic_only: true` 的虚构开发记录，不能把真实个人数据写进套件夹具或验证输出。请求需当前精确 activity_ref 和 B2b 材料 context；context 的用途 binding 改变后重新核对材料。所有写动作携带 expected_state_revision／operation_id，经原共享提交；授权、预算、对象修订和控制以当前组件为准。

`open/resume` 只读，返回用途就绪状态或受限原因。open 的 learner_packet 只包含题面与 visible_input，没有备用帮助／教师参考；不得把返回就绪称为已经展示。resume 从最新合法依据与最后可信事件定位父产物／下一连接，缺动作保持未知。角色、模式名称和 entry_actor 测试配置不认证真实身份。

`record_initial/record_help/record_revision/record_feedback` 保存已有活动中的实际事实。原答／修订使用受控 ArtifactRef，原件不原地覆写；同题仍同事件／样本。反馈引用既有 branch_index，并通过 observation 的 artifact_ref／quote 定位原答；检查可定位性不证明反馈内容正确或原因诊断成立。帮助按实际 visibility、代做操作及顺序保存，备用参考不自动展示，显示不明保持 unknown。

`checkpoint/close/return_parent` 保留可信事件、停止原因、未完成目标内要求和同一规范父产物连接。预算缩短停新展开、保存反馈和断点，不能降低目标判据。existing_need_ref 只返回沿同需求的更新候选，不写需求或排计划；提出、接责和安排的实际状态由对应责任方维护。

## 结果与限制

结果均标 synthetic_only true、scoring not_executed；只读结果 mutated false。ready／candidate 只表当前声明可用或待处理；committed 表事实保存成功，不表示任务正确、正式目标通过或 AG3 已复核。conflict 重读当前状态再决定，rejected／blocked 说明受限项和待处理责任，not_saved 保持待保存。

初答／修订保存成功后返回 `assessment_handoff`，含精确 `event_ref`、`response_point`、完整 `material_context` 和暴露完整性声明；调用方可显式送已有 B3a 检查。C0 不自动调用评分，不产 Judgment、DiagnosticNote、ActivitySpec 采用、LearningNeed 处置或 PlanCommitment。设计输出与需求补充可作为 Skill 候选交接，不能混为已保存的专业决定。Encoding／Post、SK05、七 Skill 安装、宿主身份、UI 展示认证、自动 Agent 接责和旧输出隔离不属于本批。

恢复与写入先检查删除、暂停和用途限制，不用旧摘要、请求文件或 stdout 恢复已删内容；本数据库之外副本与已加载上下文由调用者／宿主处理。SQLite 内控制成功不证明旧执行者已停止发言，当前仅用可控单入口顺序调用。

通常只加载本 Skill、C0 当前规则、精确活动／目标／材料与原答、实际帮助和断点。重要内容核验回实际原件／推导／测试；未覆盖或冲突时回相应设计依据。无需常驻研究全文、全策略库或个人全档。有限软件测试和 Skill 前向试用分别报告，真实 V1—V4 及学习收益保持独立待验证。

共同嵌套表示见 [B3 互通约定](../../../../contracts/b3-interop.md)。`timeline_completeness` 不因空列表而确定；`method_config_refs`／`strategy_context` 在执行时核采用、材料绑定与当前用途，并记录在同一事件。恢复可沿原事件或断点取回配置，不能静默替换已经使用的配置。实际偏离仍记事实，待 B3a 按所选响应点限定资格。
# B4 专项入口补充

Encoding／Post 与 AG1 关键设计使用 [B4 请求](../../../../contracts/teaching-b4.md) 和 `src/runtime/learning_teaching_b4.py`；同一 LearningStore、C0 事件、帮助、配置、checkpoint 和预算。脚本参数为 `--workspace/--request/--actor AG0|AG1`。下列 B3b C0 接口继续有效，专项活动使用 B4 入口检查 metadata。直接旧入口不检查专项声明，单入口自动路由仍属 B5。
