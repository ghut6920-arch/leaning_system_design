# AI 个人学习系统：B6 工作网络与受控宿主 v0

日期：2026-10-03。承接 [Agent 与 Skill 工作网络及实施路线 v0](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md) 的 B6，以及 B0—B5 的共享记录和专业服务。

本批落实一个有限本地工作网络：四个逻辑角色实际加载角色／Skill 规则，通过本地宿主签发的能力对象提出、接责、处理和采用工作单；AG0 的教学展示受当前执行代次约束。宿主保持单工作区独占和串行，使用明确虚构记录。真实模型、真实课程和个人保存范围仍未绑定，异步后台及并行教学展示未启用。

## 实现与交付

| 交付 | 行为 |
|---|---|
| [NetworkHost](../../personal-learning-suite/src/runtime/network_b6.py) | 四角色加载、能力对象、工作区宿主锁、串行调用、工作单接责／返回／采用、最小上下文及控制 |
| [共享记录组件](../../personal-learning-suite/src/runtime/learning_store.py) | 专用 `set_execution/check_execution`；原子接管、CAS、幂等、控制优先、旧执行者拒绝 |
| [局部契约](../../personal-learning-suite/contracts/network-b6.md) | `pl-network/0.1.0` 输入、状态、专业调用和可保障边界 |
| [SK00](../../personal-learning-suite/src/skills/personal-learning/SKILL.md)／[宿主参考](../../personal-learning-suite/src/skills/personal-learning/references/network-host.md) | 按需加载网络规则，保持可靠已有工作短路径 |
| [B6 验收](../../personal-learning-suite/specs/b6-acceptance.md) | 身份、范围、分阶段状态、接管、删除、失败、重开及 B1—B5 回归 |
| [检查脚本](../../personal-learning-suite/scripts/check_b6.py)／[演示](../../personal-learning-suite/scripts/demo_b6.py) | 保存逐项真实软件检查输出；虚构空间首次初始化，已有空间只读重开 |

`WorkOrder`、`WorkResult`、`ControlState` 使用既有规范对象和同一 SQLite。共享协议保持 `pl-contracts/0.1.0`，承载仍为 `pl-store/0.1.0`。未增加第八个 Skill、掌握数据库、复习队列或另一个总预算。原设计／研究来源和旧批报告保持原文。

## 宿主和阶段含义

宿主签发的能力对象绑定本宿主实例、角色、已加载规则与工具范围。JSON 中的角色、owner 或 mode 不替代该对象。角色规则加载及本地通道绑定不等于模型已启动，也不等于取得自然人身份认证。正式专业授权继续由 `verified_for_fixture` 的虚构授权记录声明，本批不将它升级为 `host_verified`。

工作单提出后仍由发送者跟进；仅收到不能变成接责。接收者接受全部或部分范围时留下具体责任、未接部分和触发。没有可核对接收者授权时保存候选未就绪，不能执行。专业动作使用工作单明确的固定 B5 动作及原服务，在当前控制、范围、精确依据和共享预算下运行。

返回的 `WorkResult` 保留候选阶段；当前专业责任显式采用、部分采用、重核或拒绝。网络结果采用不替代 GoalSpec、Judgment、MaterialUse 或 PlanCommitment 的原专业保存和采用门。接责不等排期、排期不等学习发生、活动完成不等目标通过。需要改变承诺时继续由 SK05 实质处置。

旧版本可用范围由当前责任重核，程序保守检查当前引用并保持不相容决定未采用。新的合法原答由教学服务单独保存，不能以迟到总结补造原答，不能以网络结果覆盖当前安排。

## 接管、展示和删除

接管校验当前活动、目标、材料、授权、预算及已记录上游依赖；接任者通过已有恢复路径核对父产物、帮助与可信断点。宿主结束旧入口的同活动展示能力，通过专用事务推进执行代次；旧能力持有原回执也不能继续展示或执行。没有结束摘要时复用原可信事实，未知动作保持未知，不触发整章重测。执行权回执不证明原答已被完整阅读。

后台角色只返回当前入口。`present` 从原专业服务产生的有限学习者载荷展示，不能把完整专业返回中的教师参考、候选解释或全档案当作用户输出。准备好与实际展示仍由教学事件的真实声明分开记录；本地函数返回不证明 Codex 窗口实际显示。

控制先于读取、保存、重试、采用与展示。删除通过原两阶段组件清理受控原件、历史、工作单、候选和已记录派生依赖；相关本地能力终止。删除索引后不保存个人内容的高水位／指纹作为暗中恢复路径，旧能力失效与新随机执行者共同阻止旧通道重新生效。后续仅以剩余合法记录建立新上下文。

受控边界是本地可信进程中的宿主管道。直接调用旧开发脚本、共享文件系统的任意写入、外部聊天、调用者保存的 stdout 和已返回对象均不在宿主隔离或删除保证内。宿主不保留个人上下文／结果缓存，但不能清除调用者或外部模型已经拿到的内容；必要时调用方实际结束该任务。本批按路线中的降级条件保留串行范围。

## 运行与验证

项目根运行，Python 3.10 及以上，仅标准库：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b6.py --scope all
python -X utf8 personal-learning-suite/scripts/demo_b6.py --workspace "examples/workspaces/B6_虚构工作网络空间"
```

可信本地调用方也可以通过 `PersonalLearningEntry(store).open_network()` 创建宿主，使用上下文管理器释放工作区锁。角色能力由 `host.bind(role)` 签发；具体请求见局部契约。演示已有工作区只读，不能重新导入被删内容或重放专业链。

最终实际结果：

| 验证 | 结果与记录 |
|---|---|
| B6 专项 | 34/34 通过，0 失败、错误或跳过；[报告](../../personal-learning-suite/validation/b6-network-runtime-report.json)／[原始输出](../../personal-learning-suite/validation/b6-network-runtime-output.txt) |
| B1—B6 全套 | 421/421 通过，包含既有 387 项；[报告](../../personal-learning-suite/validation/b6-all-runtime-report.json)／[原始输出](../../personal-learning-suite/validation/b6-all-runtime-output.txt) |
| B0 静态 | 32/32，19 份来源指纹和本地链接不变；[报告](../../personal-learning-suite/validation/b6-b0-static-report.json) |
| 主入口 Skill | 标准检查输出 `Skill is valid!`；[记录](../../personal-learning-suite/validation/b6-skill-validation.json) |
| 独立审查 | 对象范围、授权重标、嵌套已删对象、有限结果误采用和原文读取边界已按实际反例修复；12/12 针对用例通过；[收口记录](../../personal-learning-suite/validation/b6-review.md)／[独立审查](../../personal-learning-suite/validation/b6-independent-audit.json) |
| 保存与重开 | 首跑状态修订 19；重开不导入、不重放、不接管，修订仍 19，完整性正常；[首次](../../personal-learning-suite/validation/b6-demo-report.json)／[重开](../../personal-learning-suite/validation/b6-demo-reopen-report.json) |

验证环境为 Windows、Python 3.12 和 SQLite，具体版本与逐项结果见报告。四角色演示中的 AG3 返回受限结果，明确保存 `recheck`，仍有未决责任；未把它虚构为专业通过或已安排。

本批实现与虚构检查不能证明真实学科正确性、专业采用质量、V1—V4 学习结果或四角色净收益；B7 需由真实课程、可靠材料与明确保存范围完成有限试用。
