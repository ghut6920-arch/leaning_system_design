# 正常备课的程序接管入口

用户只需提出“启动某单元备课”。AG0按原专业流程明确阶段、输入、产物和审查要求，保存用户请求原件与一份执行请求，再调用日常入口；不让用户建表、填写聊天编号或启动后台程序。

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_agents.py --workspace learning/embodied-intelligence --role AG0 start-preparation --request-file learning/embodied-intelligence/coordination/runs/本次批次/runtime-request.json
```

等价专用入口为 `scripts/start_preparation.py --workspace ... --request-file ...`。它会在现有项目数据库首次使用时自动备份并新增运行表，之后复用；自动取得实际 `CODEX_THREAD_ID`，只登记本次任务及返回原聊天的地址，复用本批次专业会话。不会接管历史任务。绑定、任务和计划由本次明确请求生成，不靠猜聊天标题或最高文件版本。

成功必须同时具备：原聊天/CLI宿主预检、持久计划、实际在线Python进程与匹配租约，以及同一数据库事务保存的启用状态和 `preparation_takeover` 回执。`runtime_takeover:true` 后，AG0给用户一句实际状态并结束当前轮；不能再调用模型等待、sleep、wait_agent维持协调。后续只在具体工作或判断就绪时唤醒原线程。无变化时不通知。接管失败明确返回问题，修复接管，不默默退回原生子Agent轮询；用户明确改变执行方式时按其指令处理。

Windows受限沙箱可能阻止插件访问本机桌面通信服务。此时由AG0用宿主正式的权限提升机制执行同一已审阅的启动入口，保留真实当前聊天环境；不能改走私有通信、复制身份凭据或让用户手工搭建。提升仅用于已授权的本机通信、正常专业会话和工作区文件；自动审核拒绝时按宿主规则明确报告。

## AG0生成的请求

顶层字段：`workflow_id`（每批次唯一）、`authorization_ref`（工作区内实际保存的用户请求路径）、`purpose`（原用途/限制/必要原始依据位置）、`stages`。可显式给 `deadline_ms`、`run_timeout_ms`、`report_prompt`。默认监听4小时，单个专业执行上限1小时；它们是技术上限，不是学习时间承诺。未完成工作在监听退出后保留；不能宣称仍在推进。

每阶段由AG0按原职责决定，不由程序预填专业结论：

| 字段 | 含义 |
|---|---|
| `id`、`role` | 阶段短ID；产物负责人AG1或AG2 |
| `output` | 原产物id/type，可指定validation；正式材料包用MaterialUse/preparation_sources |
| `prompt` | 有界专业任务、原用途、必要规则/原始依据位置、真实核验及结束条件 |
| `scope`、`use`、`inputs` | 原用途/范围和原API固定输入；没有输入也明确 `[]` |
| `after` | 等待哪些本批次阶段正式采用；程序不让下游模型先启动空等 |
| `review_required` | 是否需要AG3；完整备课必须有真实AG1、AG2及至少一项AG3审查 |
| `adopt` | 默认true；最终采用仍由原AG0实际判断，程序不会自动批准 |
| `from_stage` | AG1候选功能读回的源阶段；用原assign_readback精确登记，不借AG3取件 |
| `review_after` | AG3审查先等待哪些阶段完成，例如材料等待功能读回 |
| `adopt_after` | 除本阶段门禁外还要等待哪些阶段采用；禁止环形依赖 |
| `review_purpose` | AG3先取得的原用途和原始证据位置，不能填作者“已通过”总结 |
| `output_spec` | 正式材料包的成员id/kind/不可变新路径；见下文 |

`inputs`沿日常API，例如 `{"artifact":"本批次研究产物","after_task":"research","scope":["M3.2"],"use":"teaching"}`，`after_task`可写阶段ID；程序转为确切任务ID，并在采用后冻结实际版本。已有输入用原确切revision或已采用语义，不复制正文。

通常按实际需要组织AG2研究→AG1目标/设计→AG2材料→AG1功能读回→AG3反向审查→AG0采用。充分的旧依据可固定复用，不强制重做全部研究。材料设 `review_after:["readback"]`，读回设 `from_stage:"material"`；材料先采用，读回成果再沿原依据门禁采用，不能把材料采用依赖于读回已采用制造环形依赖。候选读回的暂定确认须由AG1明确返回 `allow_provisional:true` 和成立边界，不能由程序补造。

任务ID自动为 `workflow_id-stage_id`，节点提示自动附上实际任务和结果协议。阶段均需实际交付和明确作者意见。程序按原API保存，不把结束轮次当作交付、确认或采用。AG3使用独立上下文：先只给原用途/原始依据提出问题并结束一轮，再在同一审查上下文取得确切作者版本和自己的问题进行审查；不谎称不同模型或盲评。

## 多文件材料

AG2只返回文本，Python只写计划提前声明的新路径；不放宽CLI写权限，不执行生成的代码。

```json
{"kind":"preparation_sources","members":[
  {"id":"task","kind":"formal_task","path":"questions/visible/BATCH/task-v1.md"},
  {"id":"mainline","kind":"mainline","path":"materials/BATCH/mainline-v1.md"},
  {"id":"reference","kind":"teacher_reference","path":"questions/teacher-reference/BATCH/reference-v1.md"},
  {"id":"report","kind":"material_report","path":"artifacts/BATCH/report-v1.md"}
]}
```

节点的 `output_spec` 使用上述结构；AG2的结果 `output` 为JSON字符串 `{"files":[{"id":"task","content":"实际完整正文"},...]}`，恰好覆盖全部成员。Python核路径、内容、冲突和当前派发，再保存原字节、计算指纹并调用原 `build_map` 生成清单。`deliver.path`仍为`$output`，本时指向清单。文本、教师参考、代码与核验义务不因传输格式改变；程序字节匹配不能替代专业正确性。需要图像、外部检索或执行核验而当前宿主无法完成时，明确缺项，不能伪造完成。

## 重复启动与中断

同一请求/工作流/聊天重试复用原任务、计划、专业线程和绝对截止时间，不重新建表、不重复派发。更改原请求、原授权文件或原聊天时拒绝覆盖，使用新的明确批次或先处理原在途工作。显式停用的计划不会被重复启动自动打开。启动结果未知时先核原监听及派发记录，不盲目启动第二进程或重发模型任务。

检查真实状态使用 `coordinate_runtime.py --workspace ... status`；手工 `migrate/bind/plan/run` 仅用于诊断和专项验收，不是新聊天的日常步骤。桌面/通信服务仍需在线；应用重启恢复未验收，失联保存待办，不替换AG0。
