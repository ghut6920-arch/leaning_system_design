# B2b 材料运行切片 pl-materials/0.1.0

日期：2026-10-03；共用协议仍为 `pl-contracts/0.1.0`，保存承载仍为 `pl-store/0.1.0`。
这是 [共享契约](shared-contracts.md) 对 `SourceFragment`／`MaterialUse` 嵌套字段的开发适配，未另建学习对象、数据库或共享字段表。

## 能力与判断边界

[learning-materials](../src/skills/learning-materials/SKILL.md) 指导 AG2 完成读取、准备、核验和纠错。Python [MaterialsService](../src/runtime/learning_materials.py) 检查精确引用、声明完整性、用途兼容及已标注的潜在代做；专业正确性仍由 AG2 根据实际原文、推导、测试或领域核验建立。返回 `compatible` 只说明**声明与引用符合本切片**，不能当成数学证明、图像已核、程序测试通过或独立专业审查。

只处理明确标记的虚构工作区。CLI 使用测试配置 `entry_actor=AG2`，不认证身份；未绑定常驻 Agent、网络委派、七 Skill 安装或真实课程。读取、检查和追踪只读；`submit` 经原 `LearningStore.commit`；`change --restrict` 使用原限制 API。没有教学展示、评分、补测、计划生效或专业限制恢复 API。

## 片段读取

`LearningStore.read_artifact_segment(artifact_ref, start_line, end_line, intended_use='material_read')` 在同一 SQLite 读取快照里检查删除、暂停和用途门禁。行号从 1 开始、首尾包含，整段必须存在，`locator` 必须在所选文本中；仅返回这一段。原件是受控逻辑路径、`synthetic_fixture`、不可变 revision=1；不访问外部任意文件。

`read_fragment` 请求包括 `fragment_id`、`source_ref`、`artifact_ref`、`start_line`、`end_line`。返回候选 `SourceFragment` 及文本，`read_scope.text` 仅标记 `text_extraction_only`；公式和图像保持未知，主张与内容核验保持待查。它不保存或把提取等同于语义读清。摘录应覆盖完整意义和必要上下文，过短截取由 AG2 回原件补足。

当前 `SourceFragment.read_scope` 以 `text/formula/figure` 三个 Fact 表达；`unread_parts` 为 Fact。图表、代码、视频等细分范围可在 Fact.value 中按对象保留，本批未提供对应解析器。旧 B0 片段继续保留历史结构，进入本检查器前须作显式适配，不能把旧字符串自动转换成已知事实。

2026-10-04 与 B2a 对齐：此模态字典及 `verification.content` 也是目标入口可接受的统一来源载体。目标检查使用 AG2 显式给出的 `verification.content.required_modalities` 确认该核验范围；当前材料用途仍按 context 的 `required_modalities` 检查，不由来源范围替代。统一来源的非必需模态 unknown 保持 unknown；当新材料用途需要该模态时返回 `required_modality_unread`。B2a 旧单 Fact 来源仍可完成历史目标预览与保存，但材料阶段返回 `modality_facts_required`，须 AG2 显式补齐；这属于合理专业输入缺项，不再要求目标阶段使用另一种不兼容来源形状。没有运行自动迁移或来源核验升级。

## 用途与双轴核验

`inspect_material(material, context, incoming=None)` 接受完整 `MaterialUse` 和当前活动用途。context 必备 `goal_refs`、`activity_ref`、`intended_use`、`purpose`（teaching／independent／comparison）、`required_modalities`、`conditions`。目标须匹配活动；`required_modalities` 只要求本用途实际依赖的模态。每个被引片段须读清相应模态，本批采用保守逐片段检查；复杂互补片段请由 AG2 重组为足够的读清范围，不自动猜测跨片段补全。

`verification.content` 与 `verification.use` 各保留 `status`（supported／partial／pending／error）、`checked_revision`、`scope`、`conditions`、`unchecked_scope`。content 另有 `reviewer=AG2`、`method`（source_comparison／derivation／test／expert_review）、`anchor_refs`、`domain`、`domain_checks`。use 另有 `reviewer=AG2` 和与 context 精确匹配的 `binding`。改变用途、目标、活动、条件或材料修订需重新核对；不能仅沿用内容结论。

锚点使用精确 ObjectRef 或受控 ArtifactRef；文本锚点再给 `start_line/end_line`。存在、可读和定位只是可审查性检查，不证明它支持当前结论。真实推导、测试输出、对象域、多解、边界和未核范围应在锚点原件中。不能把模型同意、研究支持某策略或有限算例写成一般性证明。

`domain_checks` 的每项用 Fact 标识具体核查；不适用可说明理由。该层为本地检查导航，具体内容按 [领域规则](../src/skills/learning-materials/references/domain-checks.md) 建立：

| domain | 必须说明的核查维度 |
|---|---|
| math | domain、inference、boundaries、completeness |
| ai | specification、environment、normal_cases、edge_cases、interpretation |
| finance | assumptions、units、data_time、scenario |
| politics | sources、fact_interpretation_values、competing_explanations、causal_limits |
| general | source_fidelity、conditions、scope |

`visible_input/backup_help/teacher_reference` 各为条目列表，条目有 `content`、`provided_operations`、`channel`。channel 可以标正文、标题、颜色、位置、默认选项等。检查器将这些**声明的**操作与活动 `learner_operations` 比较；独立用途当前可见部分代做目标操作则受限。备用帮助和后台参考仅标潜在帮助。没有标注的语义／视觉泄露仍须 AG2 人工核查。

准备包的 `actual_exposure` 固定为 unknown Fact；实际显示和时序由 AG0 的 `PerformanceEvent` 记录。不能在材料准备时声明已展示或无帮助。允许开卷前提不因此成为代做，判断针对关键操作。

## 提交与返回

`submit_material` 只提交 AG2 的 SourceFragment、MaterialUse、WorkResult；完整对象仍由唯一共享字段表校验。请求含 `expected_state_revision`、`operation_id`、`changes`、`authorization_refs`、`adoption_refs`、必要 context。AG2 材料授权须已经存在；不得同批新造授权。SourceFragment 现在也经专业授权与采用入口；这不改变 B0 历史导入。

本切片只保存检查为 compatible 的正常用途材料；partial／pending／error 返回受限候选，不通过助手当作正式可用包。候选可在调用方合法临时上下文中审查，未由本助手管理落盘。SourceFragment 的读取事实可单独提交而内容仍待查。WorkResult 须对应已接责的 AG2 WorkOrder 且决定类型一致，专业返回与计划采用分开。

实际提交沿用 CAS、当前依赖修订、幂等、角色／授权／采用和删除门禁。旧候选无法覆盖新版本；同逻辑操作重试不会多建材料、样本或需求。当前辅助器不会自动将不兼容旧依据改成新引用。B1 的专业限制暂不可解除；修正依据并不恢复历史判断或实际教学。

## 更正与双链

`trace_change` 从现有 ObjectRef 反查已记录依赖，保留字段关系及 content／requirement 导航，输出材料、历史判断、教学误导、计划四项独立的 pending 责任。`unknown_dependencies` 保持 unknown；字段分类只是导航，不能认定所有语义影响已找齐。原答、当时帮助、目标和承诺均不被追踪操作修改。

`change --restrict` 在追踪前限制 changed_refs 对应对象的指定用途；这是持久控制门，不伪造完整 ChangeNotice 采用或专业恢复。发现疑误先隔离相关用途，再由 AG2 核材料、AG1 回查目标判据和受影响安排、AG3 重评原答、AG0 修复实际误导。原答足够时不自动另考。无关片段继续有据范围，未能排除的依赖保持受限。

CLI request 文件和 stdout 是调用者副本；本组件删除只覆盖共享 SQLite 中受控材料和依赖。不要把真实个人数据写入套件 fixtures、通用领域资源或验证报告。磁盘清理不等于终止已加载上下文；相关任务及外部副本控制仍须宿主落实。
