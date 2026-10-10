# AI 个人学习系统：B5 单入口纵向集成 v0

日期：2026-10-03。承接 [Agent 与 Skill 工作网络及实施路线 v0](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md) 的 B5 清单，以及 B0—B4 的共享规范、专业服务和虚构验收。本批提供 SK00／AG0／AG1 的开发态单入口串行集成；真实宿主身份、后台接责和执行隔离继续留 B6，真实学习试用留 B7。

本批目标是让同一个入口从目标与材料，经活动、原答帮助、条件化判断、同一后续需求及安排，回到合法断点与父产物。专业内容、核验、评分、采用、成本和实际显示仍由调用方显式提供；程序连接并检查原服务，未配置或启动真实学习 Agent。

## 本批实现

| 交付 | 行为 |
|---|---|
| [单入口服务](../../personal-learning-suite/src/runtime/entry_b5.py) | `SingleEntryService.execute(envelope)` 顺序调用固定专业动作，保留阶段、控制、未决和部分失败 |
| [主入口](../../personal-learning-suite/src/runtime/personal_learning.py) | `PersonalLearningEntry.execute(request)` 与 `execute --request`；原 start／resume／route 保持只读 |
| [B5 局部接口](../../personal-learning-suite/contracts/entry-b5.md) | `pl-entry/0.1.0` 请求、动作／责任、精确绑定、CAS、保存与重试边界 |
| [SK00](../../personal-learning-suite/src/skills/personal-learning/SKILL.md)／[纵向工作流](../../personal-learning-suite/src/skills/personal-learning/references/vertical-workflow.md) | 按已有可靠工作选择够用路径，候选、正式保存与未决分别报告 |
| [AG0](../../personal-learning-suite/src/agents/AG0-coach.md)／[AG1](../../personal-learning-suite/src/agents/AG1-design-planning.md)／[SK00 任务单](../../personal-learning-suite/specs/skills/SK00-personal-learning.md) | 更新当前串行能力，保留原专业责任与宿主边界 |
| [B5 验收范围](../../personal-learning-suite/specs/b5-acceptance.md) | 纵向链、短路径、帮助继承、需求去向、控制、CAS、失败和旧基线回归 |

本批没有更换共享对象版本，`pl-contracts/0.1.0` 仍是唯一规范来源，LearningStore 仍是唯一正式记录组件。目标、材料、C0／Encoding／Post、评估、策略、计划服务保持原专业契约；新入口不建立第二份数据库、计划队列、总预算或掌握度。

## 使用方式与状态含义

在项目根运行 Python 3.10 及以上，仅标准库：

```powershell
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace <虚构工作区目录> execute --request <UTF-8请求.json>
```

请求携带 `entry_version=pl-entry/0.1.0`、`synthetic_only=true`、读取到的当前 `expected_state_revision` 和明确 `steps`。每个写步骤有自己的 `operation_id`；步骤 actor 按专业责任映射、CAS 沿前步实际结果推进，调用方不能自报身份或步骤修订。

入口提供 19 个固定专业动作。B2a 目标 package 的 SourceFragment 先由 AG2 用 goal.sources_submit 原样保存，保留原 Fact 与核验声明，不猜造 B2b 模态字段；随后 AG1 goal.submit 保存显式采用的 GoalSpec。已有相同精确引用的来源／目标须与已保存内容一致，专业决定类型不能伪标其他授权。

需要串接已保存对象时，bindings 使用前步 result 的精确返回路径，替换后步 request 的已有占位；不能引用未来、制造字段或改控制字段。专业候选可以继续做候选检查，成为正式后续依据仍需已保存、当前合法和充分采用。目标提交只允许调用方明确改变采用相关三项，不自动把候选升为正式目标。

`completed` 只表示请求中的调用全部返回可继续结果。每步同时保留原专业 status 与入口 stage，只有 `committed` 标为 `saved`；候选、有限支持、检查就绪分别报告。保存 Judgment 不证明永久掌握，提出需求不等接责，专业采用不等有效排期。学习者视图区分当前工作、活动事实、条件支持、本次关联需求及当前控制；需求带 goal_ref，不展示无关课程全部需求或教师参考正文。

整条 chain 由多个原专业事务组成。根 CAS 过期整链拒绝；中间失败立即停止后续，已保存前缀保持、返回 `partial`，未决说明 owner／decision_needed／next_trigger。继续需要当前控制和修订及经复核的剩余请求，不自动重放整链或后台续跑。单专业步骤仍可按原 operation_id 幂等重试，控制优先于旧成功回执。

## 足够证据和恢复的短路径

已有可靠活动直接进入 C0／Encoding／Post，不为每题调用三方会签；已有原答直接交 SK04，已有合格证据直接交 SK05减少投入。普通活动并不要求先遍历策略库或形成新关键设计。

同题初答、帮助和修订维持同一事件／样本；局部 Encoding 够用后回同一父任务，暴露历史和预算不归零。教学收束沿同一 LearningNeed，need.submit 仅新 ID 提出／待处理，已有需求更新由计划服务处理。close 后续候选仅在同链计划保存该稳定需求的实质非 pending 去向后解除对应未决；只收到或接受仍未处置。有效计划保存后才显示安排。

原 `resume` 和计划恢复只检查合法依据、父产物、帮助和最后可信断点；无结束摘要不重测整章，不推断未记录动作。解除用户暂停不解除专业限制。必要时间条件未知或未满足仍未完成，不靠即时加题补成后续证据。

## 验收与证据位置

本批验收依据 [b5-acceptance.md](../../personal-learning-suite/specs/b5-acceptance.md)。行为测试须保留逐项原始输出并回归 B1—B4；静态检查维持 B0 原始来源、规范与链接，Skill 检查验证精简入口及按需引用。实际通过数量和环境结论以同批生成的报告为准，不能从本文的实现描述推断测试通过。

最终实际结果：

| 验证 | 结果与记录 |
|---|---|
| B5 专项 | 38/38 通过，无失败、错误或跳过；[报告](../../personal-learning-suite/validation/b5-entry-runtime-report.json)／[原始输出](../../personal-learning-suite/validation/b5-entry-runtime-output.txt) |
| B1—B5 全套 | 387/387 通过，含原 B1—B4 的 349 项；[报告](../../personal-learning-suite/validation/b5-all-runtime-report.json)／[原始输出](../../personal-learning-suite/validation/b5-all-runtime-output.txt) |
| B0 静态 | 32/32 通过，19 份来源指纹不变，4 角色／7 Skill 与本地链接检查通过；[报告](../../personal-learning-suite/validation/b5-b0-static-report.json) |
| 独立审查 | 权限、异常输入、需求对账、展示范围、下一责任及新来源接入问题已修复并沿原反例复验；[审查记录](../../personal-learning-suite/validation/b5-review.md) |
| SK00 | 标准 quick_validate 输出 Skill is valid；独立缺摘要／缩时／争议场景只产候选，未虚构保存或安排；[前向输出](../../personal-learning-suite/validation/b5-skill-forward-output.md) |
| 保存与重开 | 同一虚构空间状态修订 6；再次运行无初始化、无重新执行、修订不变，恢复及完整性正常；[首次报告](../../personal-learning-suite/validation/b5-demo-report.json)／[重开报告](../../personal-learning-suite/validation/b5-demo-reopen-report.json) |

验证环境为 Python 3.12、SQLite 和 Windows，具体版本见报告。新目标另有从只有 AG1／AG2 授权的业务空库出发，经 goal.review、goal.sources_submit、goal.submit 保存两份来源及明确采用目标的正向测试；来源原核验声明不转译。七步演示保存的是候选判断，需求真实暂缓，未把它变为已采用能力结论。

可直接查看 [七步请求](../../personal-learning-suite/fixtures/b5-entry-request.json)，或从项目根运行：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b5.py --scope all
python -X utf8 personal-learning-suite/scripts/demo_b5.py --workspace "examples/workspaces/B5_虚构单入口学习空间"
```

演示空间须明确标为虚构，首次导入人工夹具、后续只读重开；已有空间不重新导入或补填删除内容。重开检查当前修订、完整性、已保存原答帮助、判断、需求去向与恢复位置，不把请求夹具当作当前修订下任意可重复执行的 CLI 请求。

## 当前边界与后续

当前串接是一个开发程序入口在测试授权内按专业责任顺序调用。角色名不认证身份、开发子代理不等于已部署 AG1／AG2／AG3、返回结果不等于独立复核。入口不创建网络 WorkOrder、后台接责回执、日历提醒或宿主显示拦截；程序不能阻止另一 Agent 在聊天中发言。

SQLite 中受控原件及派生记录继续使用原暂停、限制、删除和引用检查。stdout、请求文件、外部副本与已加载会话上下文不扩大删除承诺；删除后只能以剩余合法依据继续。学科正确性、合法不同解、真实成本／时间、专业采用质量和实际展示仍是有来源的调用方声明。

B6 在本串行路径上落实真实宿主、四角色工作单／接责／采用、后台控制与接管，验证旧执行者不能继续展示及删除不复活；不能保证的能力保持禁用。B7 再实例化真实课程和获授权记录，分开观察 V1—V4、必要延迟证据与组织增量。本批人工虚构贯通不能证明真实学习收益。
