# AI 个人学习系统：B3b 教学共同核心 v0

2026-10-03 联合接口更新：已统一任务资格、明确暴露完整性、复验本次采用配置并提供 B3a 响应点交接。当前 B3b 47 项检查通过，见 [联合评估与修复](AI个人学习系统_B3联合接口评估与修复_v0.md)；本文件下列 39 项及演示结果记录首次交付。C0 不自动评分，旧演示事实不升级或重填。

日期：2026-10-03。承接[Agent 与 Skill 实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第十二节 B3b、D04 C0 第二至八节、D02 证据边界与 D08 连续性；沿用 B0／B1／B2a／B2b 的共享契约、保存入口和有限目标／材料。

状态：C0 有限开发实现与本批软件验收已完成。39 项 C0 行为测试通过，B0 静态检查及 B1／B2a／B2b 回归通过；演示空间完成保存与只读重开。所有运行资料、回答、预算、授权及展示声明均为人工虚构；Skill 未安装，未执行真实课程教学或学习效果验证。

| 本批工作 | 交付 | 实际边界 |
|---|---|---|
| SK03／C0 | [教学 Skill](../../personal-learning-suite/src/skills/learning-teaching/SKILL.md)与[C0 规则](../../personal-learning-suite/src/skills/learning-teaching/references/c0.md) | AG1 关键设计候选、AG0 授权执行；Encoding／Post 专项不在本批 |
| 活动请求契约 | [teaching-b3b.md](../../personal-learning-suite/contracts/teaching-b3b.md) | 共享字段保持 `pl-contracts/0.1.0`，专业请求 `pl-teaching/0.1.0`；不另建数据库或掌握度 |
| 教学运行器 | [TeachingService](../../personal-learning-suite/src/runtime/learning_teaching.py) | 读取已有可靠简单 ActivitySpec，不生成／采用活动、正式评分或诊断 |
| 初答／帮助／修订 | 同一 PerformanceEvent、不可变原件、暴露时序 | 记录初答前后实际帮助及代做操作；未知显示／接触不解释为无帮助 |
| 分支反馈 | 原答观察锚点、既有分支、可靠参考声明及学习者后续工作 | 检查引用和声明，不自动判定学科语义或原因诊断 |
| 收束与父任务 | SessionCheckpoint、原规范父产物与返回连接 | 活动结束、局部够用和目标支持分开；同需求更新只返回候选，不自行接责或排期 |
| 受控提交与恢复 | 原 LearningStore、CAS、幂等、控制与删除门 | 当前限定虚构单入口顺序执行，不认证宿主显示或拦截旧进程输出 |

软件的 `open/resume` 返回只读范围；`record_initial/record_help/record_revision/record_feedback` 保存实际声明；`checkpoint/close/return_parent` 保存连续性事实。原答和修订始终分开，同题不新增独立成功。备用帮助与教师参考不出现在 open 的 learner_packet；准备材料不自动形成显示回执。

本批不实现或串接 B3a 的正式判断、诊断与重要复核，不改变 B3a／B3c 并行工作的各自交付状态。需要评分或内容处理时保留原答和精确条件交对应责任方；缺授权、缺核验不能用补测掩盖。B4 专项和正式计划、B5 自动纵向集成、B6 真实宿主绑定仍按路线处理。

实际验证入口是[有限验收](../../personal-learning-suite/specs/b3b-acceptance.md)与[行为检查脚本](../../personal-learning-suite/scripts/check_b3b.py)。独立 Skill 前向执行的[原始交付](../../personal-learning-suite/validation/b3b-skill-forward-output.md)保留“显示未知、预算已到、同需求未接责、父链尚未完成、非标准写法待核”的收束候选。它不提交正式记录，不代替运行器测试或学习收益证据。

| 实际检查 | 结果与报告 |
|---|---|
| C0 行为验收 | [39 项通过，0 失败／错误／跳过](../../personal-learning-suite/validation/b3b-runtime-report.json)；包含 JSON CLI 子进程、保存重开与失败边界 |
| B0 静态核对 | [32 项通过](../../personal-learning-suite/validation/b3b-b0-static-report.json)，19 个来源指纹通过，失效本地链接为 0 |
| 原组件回归 | B1 [33 项](../../personal-learning-suite/validation/b3b-b1-regression-report.json)、B2a [42 项](../../personal-learning-suite/validation/b3b-b2a-regression-report.json)、B2b [30 项](../../personal-learning-suite/validation/b3b-b2b-regression-report.json)通过 |
| Skill 结构 | Skill Creator 的 UTF-8 quick_validate 通过；独立前向输出与代码探测的修复追踪见[收口复核](../../personal-learning-suite/validation/b3b-review.md) |
| 虚构演示 | [首次保存](../../personal-learning-suite/validation/b3b-demo-report.json)为状态修订 6、同一 C0 事件修订 5；[再次只读重开](../../personal-learning-suite/validation/b3b-demo-reopen-report.json)保持相同修订，resume ready、完整性 ok |

从项目根运行：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b3b.py
python -X utf8 personal-learning-suite/scripts/demo_b3b.py --workspace "examples/workspaces/B3b_虚构教学学习空间"
python -X utf8 personal-learning-suite/src/runtime/learning_teaching.py --workspace "examples/workspaces/B3b_虚构教学学习空间" --request personal-learning-suite/fixtures/b3b-open-request.json
```

[演示脚本](../../personal-learning-suite/scripts/demo_b3b.py)首次创建独立虚构空间，保存初答、反馈、帮助、修订和收束后重新打开；已有空间只读，不重新填入已删除记录。请求文件与报告是组件之外的副本，不在 SQLite 删除范围。

本次实际空间在项目根的 `B3b_虚构教学学习空间`；[JSON CLI 原始返回](../../personal-learning-suite/validation/b3b-cli-open-output.json)为 ready、mutated false、scoring not_executed。预算保留调用方累计时长声明，缺省为未知；不自动计时或建立跨活动账本。已知时序倒置、保存失败、候选执行依据及额外参考过期均有拒绝与不新增记录的测试。

真实目标、材料及学科核验、个人原件保存范围、实际预算、模型与宿主身份仍需按[首期清单](../../personal-learning-suite/specs/pilot-inputs.md)落实。有限软件验收与人工前向执行不能宣布 V1—V4 或真实教学效果通过。
