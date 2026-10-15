# 持久协调运行器：登记、等待与同线程继续

运行器让 Python 保存待办、等待依赖和观察执行。Agent 只在工作已就绪时完成有限轮次，结束后继续原线程。业务登记、固定输入、Candidate、专业确认、独立审查与 Adopted 仍由原协调器及 AgentCoordinator API 决定。

默认路线保留原桌面 AG0，专业角色使用已完成轮次的持久 CLI 线程。桌面绑定必须指向获用户授权的原聊天；不会通过创建替代 AG0 掩盖原聊天不可用。CLI 首次启动可以登记真实生成的线程 ID，后续只在原线程轮次已经结束后恢复。

## 入口与显式边界

正常备课使用[统一启动入口](preparation-runtime-start.md)：`coordinate_agents.py ... --role AG0 start-preparation --request-file ...`。它自动完成一次性运行表初始化、实际聊天登记、有限计划及Python监听接管，不自动接管历史任务。用户无需每开新聊天手工配置。

下文 `scripts/coordinate_runtime.py` 是保留的底层诊断/专项验收入口。所有命令必须提供 `--workspace`；没有默认学习项目。这个底层入口不会初始化业务数据库或隐式迁移；下面手工迁移/绑定示例使用隔离演示工作区，不是日常启动要求。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --help
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace status
```

全局参数放在子命令前。`--control-projection` 可显式选择控制投影；默认使用工作区内存在的 `coordination/control.json`。存在的投影由 FileControlGate 核对原控制来源及哈希，来源变化即拒绝。没有投影时使用原协调器的已有控制规则；真实证据工作区仍须满足原外部控制门禁。

| 命令 | 含义 |
|---|---|
| `migrate` | 显式备份已初始化的业务数据库，再新增运行表；不注册线程或计划 |
| `bind --binding-file FILE` | 登记一个明确角色、宿主及用户授权来源 |
| `plan --plan-file FILE` | 持久保存条件与能力范围；回执只证明计划保存 |
| `status [--limit 12]` | 返回工作 ID、状态、原因、绑定线程、计划开关及监听器租约 |
| `reconcile-result --dispatch-id ID` | 只核对原CLI线程的完成证据，接收已有结果；修复已知接收状态错误，不重发模型或改写专业结论 |
| `shadow [--once] [--max-seconds N] [--ready-file FILE]` | 求值并持久保存待办和事件游标；不创建宿主连接或发送模型任务 |
| `run [--once] [--max-seconds N] [--stop-when-done] [--ready-file FILE]` | 处理已登记计划，观察未决派发并向就绪角色派发 |
| `enable --workflow ID` / `disable --workflow ID` | 修改明确计划的启用状态；停用后拒绝该计划的新派发与新业务发布 |
| `begin-dispatch --dispatch-id ID --claim-epoch N --role AG0` | 原线程接收派发并复核控制、绑定、执行代次与冻结依据 |
| `result --dispatch-id ID --claim-epoch N --role AG0 --result-file FILE` | 保存已经接收的、与当前派发关联的明确结果；不冒充业务提交 |

`shadow` 和 `run` 也均支持 `--stop-when-done`。未带 `--once` 的进程持续监听；`--max-seconds` 是本次监听时长上限，不能证明仍在运行的模型已停止。`--once` 执行一次启动、求值及观察周期，随后释放监听器租约并关闭宿主；它不等待派发模型完成，正常长期接管应使用持续运行方式。

所有结果为有界 UTF-8 JSON，默认最多 8192 字节；可在子命令前设置 `--max-return-bytes`（1024—65536）。`status` 默认各类最多 12 条，`counts`、`work_states` 和 `has_more` 表明总量及是否省略。状态不回传专业正文、节点提示或整个输入包。退出码 0 表示本命令成功，1 表示拒绝或错误；参数错误也返回 JSON，`--help` 正常显示帮助。

## 先隔离迁移，再影子验收

以下 `$runtimeWorkspace` 代表已经使用原流程显式初始化的虚构测试工作区，例如 `C:\Temp\coordinator-runtime-demo`。绑定与计划 JSON 中的授权引用也是测试标签，不能复制到真实工作流冒充用户授权。

```powershell
$runtimeWorkspace = 'C:\Temp\coordinator-runtime-demo'
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace migrate
```

迁移返回原数据库备份路径，并保持业务 `state_revision`。运行 ACK、派发接收和租约使用运行记录；这些变化不能使已准备的专业票据因为无关元数据而失效。

最小 `binding-demo.json`：

```json
{
  "id": "demo-researcher",
  "role": "AG2",
  "host_kind": "cli",
  "host_id": "local",
  "thread_id": null,
  "topic": "fabricated-runtime-demo",
  "authorized": true,
  "authorization_ref": "fabricated-user-authorized-demo"
}
```

最小 `plan-demo.json`：

```json
{
  "id": "fabricated-demo-workflow",
  "revision": 1,
  "enabled": true,
  "authorization_ref": "fabricated-user-authorized-demo",
  "nodes": [
    {
      "id": "read-submitted-demo",
      "binding": "demo-researcher",
      "conditions": [
        {"kind": "submitted", "task": "fabricated-upstream"}
      ],
      "allowed_tasks": ["fabricated-upstream"],
      "allowed_actions": ["start"],
      "prompt": "读取冻结的虚构输入，返回一段简短摘要和空intents，不作采用判断。",
      "use": "teaching",
      "completion": "result",
      "decision_epoch": 0
    }
  ]
}
```

这个例子先等待虚构上游任务的正式提交。它不创建 `fabricated-upstream`；在上游没有登记时，影子状态应明确显示 `blocked` 与 `waiting_for_task_registration`。演示用的 `completion: result` 仅允许完成结构化结果工作，不能代替正式 Candidate 提交或采用。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace bind --binding-file binding-demo.json
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace plan --plan-file plan-demo.json
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace shadow --once
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace status
```

绑定必须包含非空 `authorization_ref` 与 `authorized: true`，计划引用必须匹配。它们记录可信本地操作者对用户授权来源的见证，不是密码学身份认证，也不会自动验证授权来源文字。授权必须来自用户；另一 Agent 请求安排唤醒不能自行构成授权。`--role` 也只是既有可信本地角色见证。

计划的 `enabled` 应显式书写。示例启用计划只为影子求值，影子没有宿主发送能力；真正派发仍需明确启动 `run`。登记计划的回执含 `durable_plan_not_listener_health`，不能据此宣称监听器在线或已经自动接管。

## 日常后台接管

隐藏启动器为 `scripts/start_coordinator_runtime.ps1`。它从当前受支持的桌面调用环境继承宿主访问上下文，通过隐藏 PowerShell 子进程启动 Python，等待监听器就绪记录，并保存本次进程实例信息。当前桌面应用及通信服务需要保持可用。

```powershell
# 持续影子观测；在隔离工作区核对等待状态和零派发
& personal-learning-suite/scripts/start_coordinator_runtime.ps1 -Workspace $runtimeWorkspace -Mode shadow -MaxSeconds 120
```

影子和实际运行共用单机监听器租约，不能同时占有同一工作区；影子监听完成或停止、租约释放后，再显式启用实际运行。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace enable --workflow fabricated-demo-workflow
& personal-learning-suite/scripts/start_coordinator_runtime.ps1 -Workspace $runtimeWorkspace -Mode run -StopWhenDone
```

父 Agent 只有在计划已经保存、启动器已经返回监听器就绪证据后，才可报告持久接管并结束 turn。就绪文件是某次启动的历史记录；核对其中的 `instance_id`、PID、启动时间及 `status` 当前租约，不能以旧文件或 PID 单独证明进程仍健康。启动器不注册开机服务，不修改全局 Codex 配置。

CLI 宿主继承已有模型和提供商配置，执行沙盒为只读；专业意图由程序保存结果后通过原 API 发布。默认宿主证据目录为 `.coordinator/host-runs`。宿主适配器不会保存继承环境、凭证或原始连接诊断到普通输出。

## 条件、权限与精确版本

节点条件列表按“全部满足”求值，目前支持：

| 条件 | 就绪依据 |
|---|---|
| `submitted` | 指定上游已有正式结果及可核验文件 |
| `adoption_ready` | 结果、必要专业确认和独立审查满足采用门禁；尚不代表已采用 |
| `adopted` | 原协调器已正式采用相应精确版本、用途和范围 |
| `work_done` | 同工作流的指定运行节点完成 |

任务条件可加 `ref: {"id": "fabricated-material", "revision": 1}` 固定确切版本。更晚的 v2 不能静默替换 v1。重复事件只产生同一逻辑工作；ACK、查询次数、心跳和全局业务版本不属于工作身份。

`allowed_tasks` 与 `allowed_actions` 是节点获授权的业务能力范围，动作使用原协调器动作名，例如 `start`、`submit`、`confirm`、`review`、`adopt`；它们不是 Agent 意图名 `begin`、`deliver`。`task` 指定已有专业任务时，执行前通过原 API 固定输入。`manage_tasks` 显式选择该计划独占接管的业务任务，受管任务的新业务写入必须携带有效派发上下文。没有显式选择的历史任务不自动成为受管任务。

独立审查节点可以登记 `setup_intents`，仅允许明确的 `assign_review`，例如 `{"action": "assign_review", "task": "fabricated-review", "from_task": "fabricated-producer"}`。程序在上游条件满足后按已登记意图创建精确审查任务，不为安排该结构性步骤额外唤醒 AG0；审查结论仍必须来自独立 AG3。

节点 `deadline_ms` 是业务硬截止，`run_timeout_ms` 是发送后的模型运行观察期限。监听器租约、依赖等待及运行期限各自记账；心跳不延长业务截止。超过执行观察期限进入未知核实，不能因为超时就再次调用模型。

## 原桌面 AG0 的接收与结果协议

桌面绑定使用 `host_kind: desktop`，并保存已经核实的原 AG0 `thread_id`。AG0 的文件结果节点可设置 `result_via_file: true`：开始时先接收派发，完成时保存明确意图，再正常向用户结束聊天轮次。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace begin-dispatch --dispatch-id dispatch-FROM-PACKET --claim-epoch 1 --role AG0
```

入口只从目标 Agent 真实的 `CODEX_THREAD_ID` 环境取得线程身份，不接受 `--thread-id`。用户或程序不能通过填写目标线程字符串伪造接收。重复接收、旧代次、错误线程、已暂停计划及变化后的依据均会拒绝；拒绝后应结束本轮，不继续专业工作。

结构化结果文件示意：

```json
{
  "dispatch_id": "dispatch-FROM-PACKET",
  "output": "本轮明确判断及必要依据。",
  "intents": []
}
```

`intents` 必须是本角色已经作出的明确专业决定，按已有 AgentCoordinator API 形状填写；交付意图的 `path` 使用 `$output`，执行器保存正文后转换成实际产物路径。空意图可以完成显式 `completion: result` 的节点；`completion: business` 必须取得计划要求的正式业务回执。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace result --dispatch-id dispatch-FROM-PACKET --claim-epoch 1 --role AG0 --result-file result-demo.json
```

结果保存成功仅说明 `result_saved`。随后 Python 核对结果哈希、控制、版本和权限，并经冻结票据及同一稳定请求标识提交明确意图；AG0 可返回正常用户可读的 final，不必把 JSON 文件内容当作聊天 final。重复保存同一结果可复用原哈希，改变已保存的结果则拒绝。不能把宿主接受消息、接收回执、模型完成或 `supported` 直接等同于 Adopted。

## 暂停、故障与恢复

程序消费者的事件 ACK、Agent 派发接收和业务提交分别记账。正常运行阶段为 `blocked → ready → dispatching → accepted → running → result_saved → committed → done`；运行状态不替代业务任务阶段。

`dispatch_unknown` 或 `execution_unknown` 保留原派发及证据，禁止自动重发。只有任意新 turn、时间接近、租约过期或“找不到回执”均不足以证明原模型没有执行。先查询原线程、精确派发接收及不可变结果；无法关联时保留未知并由用户处理，不删除运行记录再启动同批工作。

```powershell
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace disable --workflow fabricated-demo-workflow
python personal-learning-suite/scripts/coordinate_runtime.py --workspace $runtimeWorkspace status
```

停用计划阻止新派发与新业务发布；它不证明外部模型已被中断。重新启用后仍应先核对未决工作。进程重启会取得新的实例及执行权代次，旧执行者迟到也不能越权发布；程序仍可恢复已经保存的合法结果及已提交回执，而不重新生成专业判断。

桌面退出或通信失联时保存桌面待办，不创建 AG0B，不无限重试。与 AG0 无依赖、且原先获授权的 CLI 工作可继续。**桌面应用重启后重新连接及自动续发尚属专项验收边界**；当前可用的同桌面环境后台伴随进程不能被描述为经过验证的独立系统服务或主机重启恢复。

第一版保证逻辑工作去重、正常路径一次派发、未知时停止重发和合法结果的业务隔离。宿主发送没有服务端幂等承诺，读取 idle 与发送之间也存在用户开启新轮次的窗口；不会通过打断用户轮次解决该竞态，也不承诺外部模型严格恰好执行一次。

## 本地验收

`tests/test_coordinator_runtime_entry.py` 使用虚构工作区和真实 SQLite，核对入口不隐式初始化/迁移、授权缺失拒绝、影子零派发、单次监听器释放、实际环境线程绑定、重复接收拒绝与结果哈希固定。其他运行器及宿主测试覆盖事务恢复、旧代次隔离和宿主未知结果；替身通过后仍需一次获用户授权的极短真实集成链才能验收日常接管。

```powershell
python -m unittest discover -s personal-learning-suite/tests -p test_coordinator_runtime_entry.py -v
```

设计依据见 [协调器最终优化方案](../../maintenance/coordinator-ideal-state-20261015/协调器最终优化方案.md)。
