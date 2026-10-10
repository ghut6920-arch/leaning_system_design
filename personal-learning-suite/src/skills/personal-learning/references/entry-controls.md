# B1 入口与控制命令

从项目根调用 Python 3（仅标准库）：

```text
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> init
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> status
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> start
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> resume --activity-id FIX-activity
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> route --intent "评分"
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> integrity
```

`init` 只初始化带虚构标记的空工作区，不建立课程、预算或学习记录。B1 不接受真实课程和个人原件；开发测试可经 `LearningStore.import_fixture` 装入明确标记的 FIX-* 对象。API 要求快照带 `synthetic_only=true`，B0 原夹具的 `synthetic=true` 由演示脚本在内存适配。可从项目根执行下列命令创建或查看已有演示空间；已有记录不重填：

```text
python personal-learning-suite/scripts/demo_b1.py --workspace examples/workspaces/B1_虚构演示学习空间 --report validation/b1-demo-report.json
```

`status` 展示引用和控制；`start/resume` 只读，缺课程、目标、活动、当前预算或执行授权时返回 `needs_input`，条件存在也只返回 `not_ready`，始终 `teaching=false`。`resume` 优先检查既有断点，否则定位活动的可信事件和 ArtifactRef；多个事件没有可核查时序时请求明确断点。ID 排序不代表发生顺序，原件正文不加载到恢复视图。

`route` 支持 SK01—SK06 的 ID、Skill 名及中文意图：目标／判据／前置 → SK01；材料／参考／内容核验 → SK02；教学／讲解／练习 → SK03；评估／评分／诊断／复核 → SK04；计划／预算／缩时 → SK05；策略／方法配置 → SK06。返回 `candidate` 与 `readiness=not_ready`，列出缺少输入；多义请求返回 `needs_input`。暂停、限制、删除和导出意图返回控制命令及所需参数，调用路由本身不变更记录。

变更必须使用 `status` 中当前修订，并保持同一逻辑操作的 `operation_id`。下面是虚构示例参数，修订以实际读回结果为准：

```text
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> pause --expected-state-revision 1 --operation-id FIX-pause-1 --scope-id FIX-activity --reason "用户暂停"
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> restrict --expected-state-revision 2 --operation-id FIX-restrict-1 --scope-id FIX-goal --intended-use "重要跳过" --reason "原依据待核"
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> resume --unpause --expected-state-revision 3 --operation-id FIX-resume-1 --scope-id FIX-activity
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> delete --expected-state-revision 4 --operation-id FIX-delete-1 --scope-id FIX-event --include-indexes
python personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构开发记录目录> export --scope-id FIX-event
```

可重复 `--scope-id`。`restrict` 无 `--intended-use` 时限制全部用途；专业恢复不由 AG0 自动完成。`resume --unpause` 仅显式解除用户暂停，默认 `resume` 只读恢复位置。删除委托共享组件，`--include-indexes` 包含受影响关联索引；不可控副本由实际报告列出。删除含持久停用门和清理两次提交，以上修订号仅为示例，每次操作均须读取实际修订。导出到 stdout，`--without-artifacts` 可省略原件正文；它声明原证据范围，调用者保存的 stdout 和外部副本不受共享组件删除控制。

导出包含所选对象的引用依赖，原件按整份逻辑文件提供。若用户只要求查看初答，按 `original_response_ref.locator` 取该段展示；不要连同共享文件里的教师参考、修订或其他内容一起回应。

`committed` 才是记录变更成功；`conflict/rejected/not_saved` 返回非零退出码并保留实际原因。`needs_input/candidate/not_ready` 是可读结果，不表示学习已发生、能力已就绪、委派已执行或后台已接责。本开发外壳没有提醒、会话展示拦截或正式专业恢复能力。

项目态共同规则链接为 [shared-contracts.md](../../../../contracts/shared-contracts.md)；发布时须生成并校验共享副本，不将当前相对依赖称为自包含安装包。
