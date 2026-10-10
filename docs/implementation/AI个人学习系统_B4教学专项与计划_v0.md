# AI 个人学习系统：B4 教学专项与计划 v0

日期：2026-10-03。基于《Agent 与 Skill 工作网络及实施路线》B4，以及已有 B0、B1、B2a、B2b、B3a、B3b、B3c 和 B3 联合修复实现。当前完成 B4 的有限开发实现与人工输入验收；所有示例均为虚构记录。七 Skill 开发源已齐，未安装或绑定真实课程、个人事实与宿主。

## 本批交付

| 范围 | 实际行为 | 实现入口 |
|---|---|---|
| SK03 Encoding／Post | 关键结构、变与不变、可接受产物、观察分支；局部双向切换、返回原产物与保存重开 | [教学 Skill](../../personal-learning-suite/src/skills/learning-teaching/SKILL.md)、[专项运行器](../../personal-learning-suite/src/runtime/learning_teaching_b4.py)、[接口](../../personal-learning-suite/contracts/teaching-b4.md) |
| AG1 关键教学设计 | 完整 ActivitySpec 候选及显式采用；目标级整体义务、整体参考覆盖、可靠局部范围与重要复核交接 | [AG1 角色](../../personal-learning-suite/src/agents/AG1-design-planning.md)、[设计与整体规则](../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md) |
| SK05 计划／AG1 计划 | 原需求接责、合并、暂缓、不投入、证据关闭、正式安排、授权缩时与断点恢复 | [计划 Skill](../../personal-learning-suite/src/skills/learning-planning/SKILL.md)、[计划运行器](../../personal-learning-suite/src/runtime/learning_planning.py)、[接口](../../personal-learning-suite/contracts/planning-b4.md) |

共享字段仍由 `pl-contracts/0.1.0` 唯一维护；SQLite 承载仍为 `pl-store/0.1.0`，C0 仍为 `pl-teaching/0.1.0`。两个新局部接口分别为 `pl-teaching-b4/0.1.0`、`pl-planning/0.1.0`。沿用现有材料、事件、判断、需求、预算和承诺，没有新建掌握数据库或复习队列。B0 原设计及研究源不修改，旧批次验收报告保留。

## 教学如何衔接

专项运行器继承 B3b C0 的资格、材料分区、实际原答／帮助／修订、授权与事务检查。局部切换将模块、栈、进入前产物、帮助边界、返回连接和观察定位追加到同一 PerformanceEvent；同题继续同一样本，父产物与预算不另发。

Post→Encoding 需要已供给允许前提、已记录实际帮助且其后有对应原答修订；备选解释和具体阻碍须保留。Encoding→Post 沿实际工作返回，不规定检索在先或统一深度顺序。进入后必须有可定位的新修订才能作返回观察；局部够用、父任务结果、整体目标支持分开。

AG1 在当前 GoalSpec requirement 的 `teaching_scope` 明确是否要求整体与整体义务。整体活动不得取消此要求；核验参考须对当前目标、判据、操作和义务有支持声明及合法原件定位。明确局部子任务可以只做严格子集，整体未覆盖仍保留。旧目标不自动补默认值，须责任方澄清，修订后材料用途重新检查。

连续整体产物交 SK04 重要复核，软件不评分。已采用、当前用途和条件内充分的旧判断可直接复用，不新加测试；最近反馈、真实帮助和时间条件交原 B3a 检查。只有目标规定的未来条件未满足时，本次收束并交同一 LearningNeed 候选，不能把日历经过写成保持支持。

## 计划如何形成

接责回执保持 `pending`；实质安排才生成 PlanCommitment。需求处置必须保留理由、不做影响和下一触发。合并要求同目标、条件、父任务；当前只支持同要求 ID 的恒等映射，接收需求完整包含源要求，整体要求不能消失。不同 ID 的专业等价关系不由本检查器推断。

一个 BudgetEnvelope 下当前一个有效承诺，多个目标共用 allocations。主动成本显式覆盖准备核验、恢复上下文、学习、反馈检查、收束切换、维护纠错；等待、系统工作和费用分别声明。未知不能当零，估计必须留余量，收束保留正时间。已保存 C0 同预算累计时长作耗用下界，不归零重领额度；此处采用最大值避免重复累计，不宣称完整自动计时。

AG0 按既有明确授权缩时，只能缩当前活动、操作、覆盖及各类投入，不能增费用、等待或系统工作；不改变目标、材料用途或关键设计。重要重排交 AG1，并在同一次提交中处置旧计划全部受影响需求。恢复重查当前专业依据、执行条件与合法断点，不凭缺摘要重启全部学习。无合格证据不关闭需求，无正式回执不称已安排。

## 实际验收结果

- [最终完整行为报告](../../personal-learning-suite/validation/b4-all-runtime-report.json)：**349 项通过，0 失败、0 错误、0 跳过**。其中专项教学 28 项、计划 29 项，原 B1—B3 联合基线 292 项；[逐项原始输出](../../personal-learning-suite/validation/b4-all-runtime-output.txt)与两个分报告同次生成。
- [本批 B0 静态报告](../../personal-learning-suite/validation/b4-b0-static-report.json)：32/32 通过，19 份来源指纹保持不变，本地链接无断链。
- [Skill 结构校验](../../personal-learning-suite/validation/b4-skill-validation.json)：更新的教学 Skill、新建计划 Skill 均通过标准校验。相对依赖沿套件布局，尚非安装发行包。
- [独立复核记录](../../personal-learning-suite/validation/b4-review.md)保留边界缺陷与修正；[独立前向输出](../../personal-learning-suite/validation/b4-skill-forward-output.md)保留人工加权均值教学候选，没有新增学习者答复、正式判断或实际计划。
- [教学重开](../../personal-learning-suite/validation/b4-teaching-demo-reopen-report.json)：状态修订 9、完整性正常，恢复 Post→Encoding→Post 历史和父任务。局部状态在中途 checkpoint 保存／重开也已测试。
- [计划重开](../../personal-learning-suite/validation/b4-planning-demo-reopen-report.json)：状态修订 3、完整性正常、只读重开；重复需求合并为一次投入，AG0 授权缩至三分钟。已有空间不重新导入或补填删除内容。

最终复核发现“缩时却增非用户投入”和“合并把整体要求降成局部要求”两条实际路径，先以负向测试复现，再修正并通过完整回归。[修正前输出](../../personal-learning-suite/validation/b4-planning-boundary-before-fix.txt)保留复现证据。独立复核确认修正封住原路径。

## 运行与定位

在 `E:\文献资料\学习系统架构设计` 执行；Python 3.10 及以上，仅标准库。本次验证环境为 Python 3.12.3、SQLite 3.46.1。

```powershell
python -X utf8 personal-learning-suite/scripts/check_b4.py
python -X utf8 personal-learning-suite/scripts/check_b4_teaching.py
python -X utf8 personal-learning-suite/scripts/check_b4_planning.py
python -X utf8 personal-learning-suite/scripts/demo_b4_teaching.py --workspace "examples/workspaces/B4_虚构专项教学学习空间"
python -X utf8 personal-learning-suite/scripts/demo_b4_planning.py --workspace "examples/workspaces/B4_虚构计划学习空间"
```

演示首次建立人工空间，之后仅只读查看。已有演示的历史状态与人工请求夹具不是任意 CLI 请求的可执行输入；请求须匹配对象、当前修订、专业用途与授权。教学 CLI 接收 `--workspace --request --actor AG0|AG1`；计划 CLI 同样参数，可加 `--inspect` 仅检查候选。请求字段见两份接口；[教学夹具](../../personal-learning-suite/fixtures/b4-teaching-open-request.json)与[计划夹具](../../personal-learning-suite/fixtures/b4-planning-input.json)用于对应人工基线。全部入口继续拒绝真实个人空间。

总入口与当前资源状态见[套件 README](../../personal-learning-suite/README.md)、[依赖清单](../../personal-learning-suite/resources/runtime-dependencies.json)和[实现取舍](../../personal-learning-suite/specs/implementation-decisions.md)。教学／计划验收范围分别见[教学验收](../../personal-learning-suite/specs/b4-teaching-acceptance.md)、[计划验收](../../personal-learning-suite/specs/b4-planning-acceptance.md)。

## 本批边界及后续接口

专业内容、完整证明、合法不同解、局部够用、实际显示、费用与方案可行性仍由责任方提供有依据的声明；程序只核结构、范围、引用、条件和控制。一次人工程序验收及 Skill 候选试用不能证明真实学习效果、完整 B10 或 V1—V4。

B5 继续落实 SK00 自动路由、调用及接责贯通；专项活动当前须显式使用 B4 入口，直接调用旧 C0 入口不会增加专项检查。B6 继续落实真实角色身份、工具和写入权限、显示与旧执行者隔离。B7 再用真实课程和获授权记录进行试用。本批没有实际计时器、日历、自动提醒或真实多 Agent 学习宿主。
