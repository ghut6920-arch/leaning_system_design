# AI 个人学习系统：B2a 目标 Skill 与 AG1 目标职能 v0

日期：2026-10-03。承接[实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第十二节 B2a、[B0 基线](AI个人学习系统_B0规范与资源基线_v0.md)及[B1 保存与入口](AI个人学习系统_B1保存与入口骨架_v0.md)。

状态：**B2a 的有限开发实现已完成。** 已交付 SK01 `learning-goals`、AG1 目标职能、目标／版本精简规则、结构化虚构候选辅助程序及验收。42 项 B2a 行为测试通过，B0／B1 复验通过，独立资料试用与最终重放均有实际产物。尚未安装 Skill、绑定真实宿主或进入真实课程教学。

## 本批交付

| 路线要求 | 实际交付 | 范围与边界 |
|---|---|---|
| SK01 目标设计 | [learning-goals/SKILL.md](../../personal-learning-suite/src/skills/learning-goals/SKILL.md)及[目标规则](../../personal-learning-suite/src/skills/learning-goals/references/goal-design.md) | 从资料与用途形成粗地图、近期目标、可检查判据、前置和证据要求，已有兼容目标可复用 |
| AG1 目标职能 | [AG1 说明](../../personal-learning-suite/src/agents/AG1-design-planning.md)与[SK01 任务单](../../personal-learning-suite/specs/skills/SK01-learning-goals.md) | 只启用目标切片；关键教学与计划待 B4，完整集成及宿主网络待后续 |
| 来源与合法判据 | 要求／内容双来源、独立关键操作、产物、正确性条件、允许资源、支持边界 | 区分课程明确、用户用途、系统建议和待澄清；程序不凭字段存在核学科真伪 |
| 版本与纠错 | [版本规则](../../personal-learning-suite/src/skills/learning-goals/references/version-rules.md)及候选兼容／变更视图 | 缩时不改标准；新要求不倒判旧答；拆并不自动搬运判断；纠错通知不冒称限制已执行 |
| 未决与有限可用范围 | 当前／远期作用域、可靠子要求、下一责任和触发 | 专属未核依据只限制关联范围；来源或授权不足保持候选 |
| 可执行辅助组件 | [learning_goals.py](../../personal-learning-suite/src/runtime/learning_goals.py)、[接口](../../personal-learning-suite/contracts/runtime-b2a.md)与[虚构输入](../../personal-learning-suite/fixtures/b2a-goal-input.json) | 检查已编写的候选和版本，stdout 只读预览；不从正文自动抽取、不采用、不评分、不另建数据库 |

公共字段及权限仍由唯一 `pl-contracts/0.1.0` 维护；B1 承载仍为 `pl-store/0.1.0`。目标规则为 `pl-goals/0.1.0`，辅助输入／报告为 `pl-goals-input/0.1.0`／`pl-goals-review/0.1.0`。新增嵌套表示是本切片适配选择，不改写 B0 历史对象或原设计来源。

## 实际验收

[B2a 行为报告](../../personal-learning-suite/validation/b2a-runtime-report.json)记录 42 项通过、0 失败、0 错误、0 跳过，原始输出见[测试记录](../../personal-learning-suite/validation/b2a-runtime-output.txt)。测试覆盖阈值边界、实现／解释区分、双来源缺项、可靠子范围、未知帮助、前置与学习者状态分开、复用和缩时、判据修订、拆并、纠错候选、坏输入，以及授权提交、重开精确读回、历史保留和暂停／来源限制拒绝。

保存测试先显式模拟虚构 AG1 人工核对与采用，再走 B1 串行入口；候选检查通过不提供写入权。测试主体、授权和核验记录都是人工夹具，不是宿主认证或真实专业回执。

[B0 复验](../../personal-learning-suite/validation/b2a-b0-regression-report.json)保持 32 项通过、19 份来源一致、本地链接无缺失；[B1 复验](../../personal-learning-suite/validation/b2a-b1-regression-report.json)保持 33 项通过。原 B0/B1 报告、15 个未执行的完整情境和设计原文保留。SK01 通过 skill-creator 结构校验。宿主为 Windows 11、CPython 3.12.3、SQLite 3.46.1。

[独立前向试用](../../personal-learning-suite/validation/b2a-forward/b2a-forward-review.md)从新的异或资料及个人配置校验用途实际生成两个个人目标；官方标准和具体配置执行仍未决。用户缩为 3 分钟并请求先看示范后，整个目标与判据修订不变，没有生成表现、掌握或有效承诺。[最终重放](../../personal-learning-suite/validation/b2a-forward-final.json)使用原输入验证修补后的行为，六项检查通过；它是根代理复验，不新增独立学习样本。

复核发现的空值／坏容器、跨能力等价映射、版本说明矛盾、无效作用域和聚合来源误限问题均已修补；最终试用还修正了读清范围与核验范围的字面混同。完整发现与复验边界见[收口记录](../../personal-learning-suite/validation/b2a-review.md)。

从项目根运行：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b2a.py
python -X utf8 personal-learning-suite/src/runtime/learning_goals.py --input personal-learning-suite/fixtures/b2a-goal-input.json
python -X utf8 personal-learning-suite/scripts/check_b0.py --report validation/b2a-b0-regression-report.json
python -X utf8 personal-learning-suite/scripts/check_b1.py --report validation/b2a-b1-regression-report.json --output validation/b2a-b1-regression-output.txt
```

## 后续接口与保留边界

目标包可交材料方和评价方，分别核当前内容用途、参考可靠性和证据可观察性。候选包含源引用，stdout 不复制来源全文，接收者须同时获得合法源包或共享精确引用；预算与示范请求沿原会话变更视图交接，不从预览补造实际发生事实。

本批未提供真实课程、个人记录、预算、模型或宿主绑定；未执行教学、正式评分、计划生效或实际示范显示。源码 Skill 依赖当前套件布局，未构建／安装七包发布套件；AG1 提示说明不等于真实角色权限。V1—V4、完整 B10 和四角色协作增益不据局部测试判通过。

工作区已有 B2b 的 SK02／AG2 材料有限切片，相关交付保持其独立记录。本次完成 B2a 后，可对齐当前目标和材料用途，再进入 B3 的证据与共同教学核心；不需要先完成整门课程图谱。
