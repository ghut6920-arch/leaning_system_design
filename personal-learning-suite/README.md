# personal-learning-suite：B0—B7 开发基线

当前学习使用：[SK00 总入口](src/skills/personal-learning/SKILL.md)及 [开始／恢复](src/skills/personal-learning/references/session-entry.md)，真实具身智能文件模式见 [MODEL_ENTRY](../learning/embodied-intelligence/MODEL_ENTRY.md)。自然学习请求直接进入所需教学工作；四角色可顺序兼任，文件模式不要求虚构 CLI 初始化。全套来源比较、新上下文实际首回合及当前边界见 [原意复审](../docs/audits/AI个人学习系统_全套Skill与Agent原意复审_2026-10-05.md)，六阶段当时的修订保留在 [历史记录](../docs/implementation/AI个人学习系统_教学内容重构_第六阶段实施与验证_2026-10-05.md)。维护或明确试用时才用 [有限验证](src/skills/personal-learning/references/verification.md)。以下 B0—B7 内容描述程序开发历史与技术范围，不作为人工学习的教学禁令。

共用协议 `pl-contracts/0.1.0`；B0 创建于 2026-10-02，B1—B6 更新于 2026-10-03，B7 第一切片开始于 2026-10-04。SQLite 共享记录和六个专业能力经 B5 串接；B6 增加本地串行宿主、四角色能力对象、工作单接责／采用及执行接管。B7 增加只读的试用配置及 V1—V4 验证引用检查。专业内容、评分、采用和成本仍由调用方提供。B1—B6 执行器仍只支持虚构开发输入；B7 不写个人记录或启动真实教学，七个 Skill 未安装，真实模型、课程和个人记录未绑定。下文各批保留程序历史范围；公开教学指令的当前核查以首段的原意复审及其验证范围为准。

项目分类见[总导航](../README.md)；实际 Agent／Skill／程序入口见[实现索引](src/README.md)，设计与研究原文见[文档索引](../docs/README.md)。本套件内部相对依赖保持，演示数据库已集中到项目 `examples/workspaces`。

当前 B6 受控本地串行网络见 [交付说明](../docs/implementation/AI个人学习系统_B6工作网络与受控宿主_v0.md)、[接口](contracts/network-b6.md)和[验收范围](specs/b6-acceptance.md)。四角色在本地宿主管道中绑定；真实模型、真实课程、Codex 聊天拦截与异步后台仍未绑定。下文旧批次描述保留历史范围。

原 B5 入口见 [交付说明](../docs/implementation/AI个人学习系统_B5单入口纵向集成_v0.md)、[接口](contracts/entry-b5.md)、[专项验收](specs/b5-acceptance.md)和[完整报告](validation/b5-all-runtime-report.json)。

入口与交付：

- [共用契约](contracts/shared-contracts.md)：对象、责任、授权、六类交付包、采用顺序与控制规则；唯一字段维护源。
- [B1 承载与控制接口](contracts/runtime-b1.md)：SQLite 单一记录来源、事务提交、精确历史引用、限制、两阶段删除与宿主边界；承载格式为 `pl-store/0.1.0`，共用协议保持原版。
- [SK00 开发入口](src/skills/personal-learning/SKILL.md)、[入口控制说明](src/skills/personal-learning/references/entry-controls.md)与 [AG0 外壳](src/runtime/personal_learning.py)：检查开始条件、恢复位置、候选路由及受控记录操作。相对依赖沿当前项目布局解析，尚非自包含安装包。
- [SK01 目标 Skill](src/skills/learning-goals/SKILL.md)、[B2a 候选接口](contracts/runtime-b2a.md)与[目标辅助程序](src/runtime/learning_goals.py)：模型设计可检验目标；程序检查结构化虚构候选、版本、可靠子范围及未决交接，保持候选，不评分或自动采用。
- [SK02 材料 Skill](src/skills/learning-materials/SKILL.md)、[AG2 角色](src/agents/AG2-materials.md)、[B2b 材料接口](contracts/materials-b2b.md)与[材料辅助程序](src/runtime/learning_materials.py)：片段读范围、用途双轴声明、分区和潜在代做检查；正常用途材料经既有共享入口保存；专业正确性依据仍由 AG2 核验。
- [SK04 评估 Skill](src/skills/learning-assessment/SKILL.md)、[AG3 角色](src/agents/AG3-assessment.md)、[B3a 评估接口](contracts/assessment-b3a.md)与[评估辅助器](src/runtime/learning_assessment.py)：原答响应点、操作级帮助、任务资格、双轴、目标内时间、冲突和有限诊断声明检查；显式受控提交，专业评分由模型完成。
- [SK03 教学 Skill](src/skills/learning-teaching/SKILL.md)、[C0 规则](src/skills/learning-teaching/references/c0.md)、[B3b 请求接口](contracts/teaching-b3b.md)与[教学运行器](src/runtime/learning_teaching.py)：可靠简单活动的资格检查、原答／帮助／修订、分支反馈、收束、父任务断点与恢复。沿同一事件和共享提交，不自动评分或排期。
- [SK06 策略 Skill](src/skills/learning-strategies/SKILL.md)、[B3c 配置接口](contracts/strategies-b3c.md)与[策略辅助器](src/runtime/learning_strategies.py)：完整资源按需读取，方法声明、材料用途、采用与本次复用分别检查。
- [B3 联合接口约定](contracts/b3-interop.md)与[分析修复记录](../docs/implementation/AI个人学习系统_B3联合接口评估与修复_v0.md)：统一任务资格、时序完整性、父任务帮助、材料用途、配置桥接和返回阶段，不重写历史事实。
- [B4 交付说明](../docs/implementation/AI个人学习系统_B4教学专项与计划_v0.md)、[教学专项接口](contracts/teaching-b4.md)、[专项运行器](src/runtime/learning_teaching_b4.py)：AG1 关键教学设计，Encoding／Post 切换与同一产物返回，整体参考与已有证据复用检查。
- [SK05 计划 Skill](src/skills/learning-planning/SKILL.md)、[计划接口](contracts/planning-b4.md)、[计划运行器](src/runtime/learning_planning.py)：接责、合并、暂缓、闭合及共享预算安排；授权缩时和断点恢复。
- [来源清单](resources/source-registry.json)与[资源核对说明](resources/README.md)：N00、D00—D11、R01—R06；实际结构核对和读取边界。
- [依赖状态](resources/runtime-dependencies.json)：设计源、运行资源、宿主和实例输入分开。
- [实现取舍](specs/implementation-decisions.md)与[首期输入清单](specs/pilot-inputs.md)：冻结范围、后续待定与真实未知。
- 角色任务单：[AG0](src/agents/AG0-coach.md)、[AG1](src/agents/AG1-design-planning.md)、[AG2](src/agents/AG2-materials.md)、[AG3](src/agents/AG3-assessment.md)。
- Skill 任务单：[SK00](specs/skills/SK00-personal-learning.md)、[SK01](specs/skills/SK01-learning-goals.md)、[SK02](specs/skills/SK02-learning-materials.md)、[SK03](specs/skills/SK03-learning-teaching.md)、[SK04](specs/skills/SK04-learning-assessment.md)、[SK05](specs/skills/SK05-learning-planning.md)、[SK06](specs/skills/SK06-learning-strategies.md)。
- [虚构快照](fixtures/synthetic-baseline.json)、[虚构原件](fixtures/originals.md)、[负向静态夹具](fixtures/static-cases.json)和[未来行为情境](fixtures/runtime-scenarios.json)。
- [B0 静态检查](scripts/check_b0.py)与[检查输出](validation/b0-static-report.json)；[B1 行为检查](scripts/check_b1.py)、[精简报告](validation/b1-runtime-report.json)与[原始测试输出](validation/b1-runtime-output.txt)。
- [虚构演示脚本](scripts/demo_b1.py)与[演示结果](validation/b1-demo-report.json)：独立空间保存、重新打开、定位断点及候选路由。

从本项目根执行（B1 使用 Python 3.10 及以上；仅标准库，当前验证环境为 Python 3.12）：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b0.py --report validation/b0-static-report.json
python -X utf8 personal-learning-suite/scripts/check_b1.py
python -X utf8 personal-learning-suite/scripts/check_b2b.py
python -X utf8 personal-learning-suite/scripts/check_b2a.py
python -X utf8 personal-learning-suite/scripts/check_b3a.py
python -X utf8 personal-learning-suite/scripts/check_b3b.py
python -X utf8 personal-learning-suite/src/runtime/learning_goals.py --input personal-learning-suite/fixtures/b2a-goal-input.json
```

B0 检查唯一契约字段表、19 个来源的指纹和定位、角色／Skill 协议与链接、虚构记录的字段关系。B1 在隔离临时目录实际检查保存后读回、旧状态冲突、幂等、权限与采用边界、暂停／限制、删除与迟到拒绝、限定导出、恢复、路径边界及失败回滚。默认结果在套件 `validation` 目录；报告只记录用例结果，学习事实仍来自人工夹具。

查看已有的虚构演示空间（位于项目根、套件之外）：

```powershell
python -X utf8 personal-learning-suite/scripts/demo_b1.py --workspace "examples/workspaces/B1_虚构演示学习空间" --report validation/b1-demo-report.json
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" status
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" resume --activity-id FIX-activity
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" route --intent "评分"
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" integrity
```

演示首次导入人工夹具，已存在的空间只查看，不覆写或重新导入已删除内容。普通 CLI 的 `init` 只建立空虚构空间。`start/resume` 只读检查与恢复，缺少当前条件时返回 `needs_input`；路由返回 `candidate/not_ready`，不会启动 Agent、生成接责回执或改正式计划。暂停、限制、删除及显式解除用户暂停的参数见[入口控制说明](src/skills/personal-learning/references/entry-controls.md)，变更必须提供当前 `expected_state_revision` 与同一逻辑操作的 `operation_id`。

导出到 stdout，范围包含所选对象的合法依赖与原件；若多个片段共用同一原件文件，导出可能包含整份文件。保存 stdout 后的副本、宿主历史与外部备份不在组件清理范围。SQLite 的记录串行提交不构成身份认证、角色写隔离或旧 Agent 输出拦截；当前只能采用单入口顺序执行。

B0 的 15 个完整未来行为情境仍保留为 `not_executed`。B1 只执行相关存储与入口切片，不能将局部通过算作完整 B10 情境、真实试用或 V1—V4 效果验证。B3b 实现 C0 虚构教学共同核心；B3 联合修复增加与 B3c 当前配置、B3a 响应点评估的显式连接，B4 专项执行与 SK05 计划的当前有限实现见末节。

B2b 新增受控 `read_artifact_segment`，可以只读定位明确的行段；原 B1 导出语义保持。材料命令 `read/inspect/submit/change` 使用 `--workspace` 和 `--request` 指定虚构工作区及 UTF-8 JSON；具体字段见材料接口。`inspect` 的 compatible 只证明声明和引用满足有限检查，不能自动证明内容正确、图已核、代码测试已运行或没有语义泄露。`change --restrict` 先设用途门，四项恢复保留各自责任，原答和实际事件保持原件。

B2b 验收入口与结果见 [有限验收](specs/b2b-acceptance.md)、[行为报告](validation/b2b-runtime-report.json)、[独立复核](validation/b2b-review.md)。本批仍为开发源，Skill 未安装，PDF/OCR、真实多模态与宿主角色绑定未实现。

[B2b 演示脚本](scripts/demo_b2b.py)只在新空间导入人工夹具和提交一份正常用途材料；已有空间只读，删除后不重填。可运行 `python -X utf8 personal-learning-suite/scripts/demo_b2b.py --workspace "examples/workspaces/B2b_虚构材料学习空间"`。本项目的独立虚构演示保存后重开为修订 2、29 个对象，结果见 [演示报告](validation/b2b-demo-report.json)。

B2a 的[验收范围](specs/b2a-acceptance.md)、[行为报告](validation/b2a-runtime-report.json)与[收口记录](validation/b2a-review.md)单独记录目标切片：42 项测试通过，独立资料试用及最终重放保留实际输入／输出。原 B0/B1 历史报告保留。SK00、SK01 和 SK02 的 SKILL.md 仍是依赖套件布局的开发包，未安装或构建七包发布套件。

SK00、SK01、SK02、SK03、SK04、SK05、SK06 均是依赖套件布局的开发源。B3b 的[验收范围](specs/b3b-acceptance.md)、[原批行为报告](validation/b3b-runtime-report.json)与[收口复核](validation/b3b-review.md)保留首次交付的 39 项测试；当前联合修复结果另存，见末节。`TeachingService.run` 和 JSON CLI 的具体请求见教学接口；B1 原入口的 start/resume/route 仍只读，尚未实现 B5 自动串接专业工作流。

[B3b 实现说明](../docs/implementation/AI个人学习系统_B3b教学共同核心_v0.md)列出交付与实测边界。[演示脚本](scripts/demo_b3b.py)可运行 `python -X utf8 personal-learning-suite/scripts/demo_b3b.py --workspace "examples/workspaces/B3b_虚构教学学习空间"`；[首次保存](validation/b3b-demo-report.json)与[再次只读重开](validation/b3b-demo-reopen-report.json)均为状态修订 6、同一 C0 事件修订 5。已有空间只读，删除后不重填。

真实课程输入继续按[首期清单](specs/pilot-inputs.md)落实。B3b 的显式暴露及时间线完整性是调用方声明，程序不认证屏幕显示；要求级判断和有限诊断由 B3a 承接。B3c 已有少量完整 Encoding／Post 资源与配置检查；B4 专项执行器及计划现已有限实现。目标候选、虚构执行与独立试用不能代替真实学习效果验证。

B3a 的[验收范围](specs/b3a-acceptance.md)、[行为报告](validation/b3a-runtime-report.json)与[收口记录](validation/b3a-review.md)单独记录 SK04/AG3 的有限切片。`inspect/diagnose` 只读，`submit` 经原保存入口；同题一个样本，有帮助条件下的支持仍保留，当前充分即停止。常规评分[授权模板](templates/routine-scoring-grant.json)为 unbound，不能直接执行。当前声明与受条件限制结果不一致时返回 limited/submission_ready=false，正式保存拒绝过宽判断。

[B3a 演示脚本](scripts/demo_b3a.py)可运行 `python -X utf8 personal-learning-suite/scripts/demo_b3a.py --workspace "examples/workspaces/B3a_虚构证据学习空间"`；已有空间只读，不重填删除内容。[演示报告](validation/b3a-demo-report.json)记录保存后重开；候选不自动采用，没有新增表现、需求或计划。SK04 仍是依赖套件布局的开发源，未安装或绑定真实宿主；B5 的单入口贯通与完整专业用途恢复继续按后续阶段验证。

## B3c 策略资源与配置（2026-10-03）

2026-10-06当前更新：全部60张Encoding卡及4个Post包已有完整可读资源。单元以理解目标和整体工作划定，备课实际接选法与所需Post；反馈后沿已备主线继续，不逐题等待“继续”。下段保留原B3c初期范围，当前资源以manifest为准。

[SK06 开发入口](src/skills/learning-strategies/SKILL.md)、[局部接口](contracts/strategies-b3c.md)、[辅助运行器](src/runtime/learning_strategies.py)和[资源清单](resources/strategies/manifest.json)已实现有限策略切片：60 卡轻索引，S07／X02／R09 三张完整双正文卡包与 R02 文首文尾规则，四份有具体出处的 Post 方法说明。其余卡只导航，R09 保持空引用和设计综合性质，Post 不固定检索在先。

辅助器提供 index／load／inspect／reuse／submit／change；完整资源仍须当前任务适配，reviewed 不等采用。正式 MethodConfig 复用 B1 的授权、采用、CAS、幂等与控制门，不另建数据库。已有可靠活动直接复用，必要条件未知保持受限；单一补全引用两卡不增加事件或样本。配置声明检查不证明内容真伪、实际暴露、合格延迟或方法效果。

[有限验收](specs/b3c-acceptance.md)与[行为报告](validation/b3c-runtime-report.json)记录软件边界；[演示脚本](scripts/demo_b3c.py)首次保存人工配置，已有空间只读，删除后不重填。当前配置输入为 `pl-strategies-input/0.2.0`：完整 `material_context` 必填并进入 review 绑定，旧配置须重核后才能当前复用；通用资源仍为 `pl-strategies/0.1.0`。B3b 通过本次请求 `method_config_refs`／`strategy_context` 显式复验配置并保留实际事件引用，B3a 按响应点和确切历史条件检查。开发 Skill 未安装，真实角色与 B5 自动路由及自动串接仍待实现；完整 B10 与 V1—V4 未验证。

```powershell
python -X utf8 personal-learning-suite/scripts/build_b3c_resources.py --check
python -X utf8 personal-learning-suite/scripts/check_b3c.py
python -X utf8 personal-learning-suite/scripts/demo_b3c.py --workspace "examples/workspaces/B3c_虚构策略学习空间"
python -X utf8 personal-learning-suite/src/runtime/learning_strategies.py inspect --workspace "examples/workspaces/B3c_虚构策略学习空间" --request personal-learning-suite/fixtures/b3c-method-input.json
```

## B3 联合修复（2026-10-03）

资格采用一个规范表示，并保守读取旧 B3a／B3b 夹具；冲突、非布尔声明和未知条件不能被有利字段覆盖。C0 显式保存 timeline_completeness；B3a 沿选定响应点评估本事件及父任务相关帮助和最近接触，未知修订时间不退回初答时间。配置用途和材料用途分别绑定，历史事件不因新配置出现自动改写。检查相容、专业采用、可继续和提交成功分别保留阶段含义。

联合行为及回归结果见[分析修复记录](../docs/implementation/AI个人学习系统_B3联合接口评估与修复_v0.md)。演示空间保持原历史，已有空间只读，删除后不重填；开发联调不生成真实学习事实或自动复习债务。

当前 [联合报告](validation/b3-interop-report.json)通过 292 项行为检查：跨包 11、B3a 82、B3b 47、B3c 47，另含 B1 33／B2a 42／B2b 30 项回归。运行 `python -X utf8 personal-learning-suite/scripts/check_b3_interop.py` 可复验。B0 32 项静态检查及 19 份来源指纹通过，资源构建器的 11 份文件一致。

旧演示空间中的非布尔资格声明、未知完整性或缺 material_context 审查绑定可能使当前执行受限；这是待专业重核的旧依据，不自动升级为新声明。新建隔离演示使用当前夹具；原空间重开只读，脚本以实际受限原因报告。原批次的成功回执不能替代新接口复验。
## B4 教学专项与计划（2026-10-03）

[教学专项验收](specs/b4-teaching-acceptance.md)和[计划验收](specs/b4-planning-acceptance.md)分别限定本批范围。专项执行器继承 C0，把局部栈、帮助及返回点存入同一 PerformanceEvent；整体活动核当前 GoalSpec 的 teaching_scope 与核验依据，局部子任务不能取消整体要求。已有采用证据在原条件与用途内够用时直接返回，不追加测验；完整产物交 SK04，程序不评分。

计划辅助器沿原 LearningNeed／PlanCommitment／BudgetEnvelope：接责保持 pending，实质安排才写承诺；合并不重复占预算，安排核完整主动成本、非用户成本及收束余量。已保存 C0 时长不能归零；授权 AG0 缩时只缩既有范围。恢复重新检查依据与活动条件，未知成本或过期材料不能继续领额度。

最终[完整行为报告](validation/b4-all-runtime-report.json)通过 349 项：B4 教学 28、计划 29，另含原 B1—B3 联合基线 292 项；[原始输出](validation/b4-all-runtime-output.txt)保留逐项结果。[本批 B0 静态报告](validation/b4-b0-static-report.json)为 32/32，19 份来源指纹不变。[独立复核](validation/b4-review.md)与[Skill 前向输出](validation/b4-skill-forward-output.md)区分程序验收、候选教学和真实效果。两个更新／新建 Skill 的标准结构校验通过，七 Skill 仍未安装。

```powershell
python -X utf8 personal-learning-suite/scripts/check_b4.py
python -X utf8 personal-learning-suite/scripts/check_b4_teaching.py
python -X utf8 personal-learning-suite/scripts/check_b4_planning.py
python -X utf8 personal-learning-suite/scripts/demo_b4_teaching.py --workspace "examples/workspaces/B4_虚构专项教学学习空间"
python -X utf8 personal-learning-suite/scripts/demo_b4_planning.py --workspace "examples/workspaces/B4_虚构计划学习空间"
```

[教学首次演示](validation/b4-teaching-demo-report.json)与[只读重开](validation/b4-teaching-demo-reopen-report.json)均为状态修订 9，恢复 Post→Encoding→Post 历史及同一父任务；[计划首次演示](validation/b4-planning-demo-report.json)与[只读重开](validation/b4-planning-demo-reopen-report.json)均为状态修订 3，合并重复需求并授权缩至三分钟。已有空间只读，不覆写或重填删除内容。新教学请求见[人工夹具](fixtures/b4-teaching-open-request.json)；计划请求见[人工夹具](fixtures/b4-planning-input.json)，必须有对应人工对象、当前修订和授权才能执行，不能直接用于真实课程。

B4 是依赖套件布局的开发源；专业内容、成本与实际展示仍为有来源的声明，程序不认证其真伪。旧 GoalSpec 不自动增加 teaching_scope；需 AG1 在真实设计中澄清，材料用途随活动修订重新核对。B5 自动路由／调用接责、B6 身份和工具隔离／显示宿主、B7 真实试用及 B10／V1—V4 继续待验证。

## B5 单入口纵向集成（2026-10-03）

[单入口服务](src/runtime/entry_b5.py)已通过 PersonalLearningEntry.execute 与主 CLI 接入。19 个固定动作顺序连接目标来源／目标、材料、方法、C0／Encoding／Post、评估、需求与计划；JSON Pointer 绑定前步实际返回引用。调用方显式提供专业声明、采用、成本与授权，程序不从原答生成评分。新目标来源先由 AG2 的 goal.sources_submit 原样保存，目标由 AG1 goal.submit 提交。

根 CAS 过期即拒绝，逐步核当前状态；中途失败保留已保存前缀并列出未执行步骤。候选、检查、有限支持、保存和 completed 分开；completed 仅说明这组调用全部返回可继续结果。既有需求经原 PlanningService 接责／处置，accept 保持 pending；收束候选与同链实质处置对账。user_view 限本次关联范围，分工作／投入、活动事实、条件支持和需求实际去向。

```powershell
python -X utf8 personal-learning-suite/scripts/check_b5.py --scope entry
python -X utf8 personal-learning-suite/scripts/check_b5.py --scope all
python -X utf8 personal-learning-suite/scripts/demo_b5.py --workspace "examples/workspaces/B5_虚构单入口学习空间"
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B5_虚构单入口学习空间" status
```

[可审阅请求](fixtures/b5-entry-request.json)为首次导入对应虚构夹具后的七步输入，根状态修订为 1；不能在已执行演示空间上盲目重放。演示已有空间只读，不重填已删除记录。[首次演示](validation/b5-demo-report.json)与[只读重开](validation/b5-demo-reopen-report.json)保留实际结果。

B1 start/resume/route 与原控制语义保持；execute 是独立显式执行命令。Skill 开发源、SQLite 和共享协议沿原套件；未安装、未绑定真实身份，不创建后台网络工作单或独立复核。完整 B10 宿主隔离与 V1—V4 学习效果留后续验证。

## B6 工作网络与受控宿主（2026-10-03）

[NetworkHost](src/runtime/network_b6.py) 实际加载四角色与对应 Skill 源，通过本宿主能力对象连接工作单、明确接责、同步专业返回与显式采用。专业动作沿用 B5 和同一 SQLite；没有新总预算、学习数据库或复习队列。执行权由 LearningStore 专用原子接口维护，当前 AG0 经代次复查返回有限 learner_packet，旧入口不能继续展示。未接责、未处理和受限范围仍有责任与触发。

本批继续只支持虚构开发输入。单工作区 OS 宿主锁和进程内串行门只保障本地管道；异步后台、并行教学、任意共享文件写入和 Codex 聊天拦截未启用或未验证。七个 Skill 未安装、真实模型未启动，规则加载不证明独立复核。

```powershell
python -X utf8 personal-learning-suite/scripts/check_b6.py --scope all
python -X utf8 personal-learning-suite/scripts/demo_b6.py --workspace "examples/workspaces/B6_虚构工作网络空间"
```

使用 `PersonalLearningEntry(store).open_network()` 的上下文管理器建立宿主，再由可信调用方 `bind(role)`。详见 [请求与生命周期](contracts/network-b6.md)、[验收](specs/b6-acceptance.md)及 [SK00 宿主参考](src/skills/personal-learning/references/network-host.md)。演示重开只读；删除后不会再次导入或重放。当前实际验证记录在 `validation/b6-*`，真实课程与 V1—V4 留 B7。

## B7 试用准备与分层验证（2026-10-04，第一切片）

[B7 交付说明](../docs/implementation/AI个人学习系统_B7有限真实试用与验证工具_v0.md)、[只读接口](contracts/pilot-b7.md)、[验收范围](specs/b7-acceptance.md)和[未配置模板](templates/b7-pilot-input.json)已新增。`PilotService.preflight/report` 核调用方提供的共享对象、原件及控制声明，返回配置缺项和 V1—V4 引用审查结果；原答与教师参考不回显，不写入数据库，不启动模型或教学。`real` 输入也不会解除 B1—B6 的虚构写入门。

主入口可以无工作区只读检查 B7；其他原命令仍须显式 `--workspace`：

```powershell
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action preflight --request personal-learning-suite/templates/b7-pilot-input.json
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action report --request personal-learning-suite/templates/b7-pilot-input.json
python -X utf8 personal-learning-suite/scripts/check_b7.py --scope pilot
python -X utf8 personal-learning-suite/scripts/check_b7.py --scope all
python -X utf8 personal-learning-suite/scripts/demo_b7.py
python -X utf8 personal-learning-suite/scripts/check_b7_coverage.py
```

检查/演示只用人工输入，实际结果另存 `validation/b7-*`，既有批次报告和演示空间不覆写。B10 索引把本次回归中的原始用例定位到 12 个有限切片；`full_scenario_status` 仍为 `not_executed`，不会把切片累计成完整 B10 或真实试用通过。

最终[B7 专项](validation/b7-pilot-runtime-report.json)通过 33 项，[完整回归](validation/b7-all-runtime-report.json)通过 454 项，失败、错误及跳过均为 0；[逐项输出](validation/b7-all-runtime-output.txt)可回查。[静态核查](validation/b7-b0-static-report.json)为 32/32，19 份设计来源指纹未变。[独立复核](validation/b7-review.md)记录四类漏拦截的修复及五项重放；这些重放已包含在上述测试次数中。

V1 内容/评价、V2 教学兑现、V3 目标表现、V4 组织增量分开报告。同题修订不增加样本，无可比起点不报学习增益；目标内必要时间/接触条件未知时保持未知，未比较不报组织优势。未知费用不当零，分轴成本与细分不重复加总。报告只核结构、引用和专业声明，仍不认证学科真伪或自然人身份。

真实课程、近期用途、实际投入和套件外的个人记录目录尚未落实，真实试用继续未执行。输入文件、原件、stdout 及调用者保存的报告不在原 SQLite 的删除控制范围；本切片只核本次是否还能使用所引用依据。落实真实承载与正式权限后，才进入正常学习及目标内后续观察。

## 架构审计修复（2026-10-04）

[审计](../docs/audits/AI个人学习系统_Skill与Agent设计综合审计及补强路线_2026-10-04.md)中的 F01—F04 已落实：检查点累计时长与事件原子保存，旧合法检查点进入教学和计划支出下界；网络待办逐结果保留并核控制；目标来源接受统一模态／核验声明并经 B5 贯通材料用途；嵌套或返回后重复展开必须有新学习者响应。匹配耗用的受限检查点阻塞继续，旧额度不能靠省略时间、收束重开或忽略限制恢复。

完整回归 [483/483](validation/architecture-fixes-2026-10-04/all-runtime-report.json)，失败、错误和跳过均为 0；[原始输出](validation/architecture-fixes-2026-10-04/all-runtime-output.txt)与各项红绿记录另存，原 454 项基线及失败探针保留。[静态检查](validation/architecture-fixes-2026-10-04/static-report.json)32/32、19 份来源通过；11 份策略资源构建一致。详细行为、旧格式兼容和当前能力见[实施记录](../docs/audits/AI个人学习系统_架构审计修复实施记录_2026-10-04.md)。

R01 的三项测试确认历史事实可按原修订回查，兼容声明不自动迁移支持；正式历史重评／跨版本支持迁移仍待实现。来源的未知模态不升级、时长仍为调用方声明、新响应的学科意义仍由专业责任判断。真实模型教学、课程／个人记录及 V1—V4 学习效果继续未验证。
