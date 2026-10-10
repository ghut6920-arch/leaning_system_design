# AI 个人学习系统：B7 有限真实试用与验证工具 v0

日期：2026-10-04。承接 [Agent 与 Skill 工作网络及实施路线 v0](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md) 的 B7，依据工作包 9/10 的跨学科边界、四类验证与首期实例说明。

本批开始实现 B7 的通用准备与报告能力：只读检查首期输入、共享对象与原件引用，分开整理 V1—V4 的可解释范围、缺项及限制。真实课程、用户投入和可控个人记录目录仍未选定，真实试用尚未开始；没有创建个人学习档案，也没有放开 B0—B6 的虚构执行门。

## 本批交付

| 交付 | 用途 |
|---|---|
| [PilotService](../../personal-learning-suite/src/runtime/pilot_b7.py) | 标准库、无持久化 `preflight/report`，核当前有限配置及四类验证引用 |
| [B7 局部契约](../../personal-learning-suite/contracts/pilot-b7.md) | `pl-pilot/0.1.0` 请求、共享对象引用、输出与控制边界 |
| [B7 有限验收](../../personal-learning-suite/specs/b7-acceptance.md) | 未配置、真实出处、原件、控制、四类结论、成本及比较边界 |
| [首期输入模板](../../personal-learning-suite/templates/b7-pilot-input.json) | 明确未配置，缺课程/预算/记录目录时仍能检查缺项，不含虚构个人事实 |
| [B10 覆盖脚本](../../personal-learning-suite/scripts/check_b7_coverage.py) | 核实际报告及原始输出，映射十二个情境的软件切片及未覆盖面；不改原情境状态 |

对象仍用 `pl-contracts/0.1.0` 的 `LearningInstance`、`GoalSpec`、`PerformanceEvent`、`Judgment`、`BudgetEnvelope` 与 `ValidationDecision`。验证只增加原事件的引用索引，不建第二套原答库、画像、统一掌握分数或实验副本。

## 能判断到哪里

V1 检查内容/评价依据可否定位，V2 检查教学过程的原事件及帮助条件，V3 检查目标表现与起点/时间条件能否支持相应陈述，V4 检查具体组织比较与完整成本。四类结果可以分别失败或保持未知。程序只核结构、声明与引用，不证明学科内容正确、用户表现真实或模型已承担专业责任。

同题修订保留原事件身份，不新增独立样本；没有可比起点不估学习增益。延迟观察由正式目标的真实用途决定，接触未知不当无接触；即时多做题不能补足时间条件。比较不是固定配额，没有同课程相近未学单元就保持组织优势未知。

成本分别看用户主动投入、阻塞等待、系统准备/核验/维护和费用；unknown 不当 0，首次构建与复用分列。同一会话细分不重复相加，退出或未执行不算“更省成本地完成同一目标”。这些数值由有依据的原记录提供，工具不自动测量。

## 输入与控制

核查接受完整共享对象、具体修订引用、原件映射及当前控制声明。`real` 中虚构 ID、`synthetic_fixture` 原件或 `verified_for_fixture` 不能充作真实依据；通过结构核查也不等于已认证真伪、自然人身份或真实执行授权。默认 host 仅说明人工单入口，`execution_available=false`。

删除、暂停和限制先于结果使用。失去原件、当前有效依赖或授权时旧“通过”不恢复用途，仍由相应专业方以合法剩余依据处理保留/收窄/撤销。B7 第一切片没有持久化或外部文件清理能力；调用者保存的输入 JSON、原件、stdout、导出和聊天不在既有 SQLite 删除保障内，不宣称这些副本已擦除。

## 运行和实际验证

项目根可从已有主入口运行，无需创建 workspace：

```powershell
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action preflight --request personal-learning-suite/templates/b7-pilot-input.json
python -X utf8 personal-learning-suite/src/runtime/personal_learning.py pilot --action report --request personal-learning-suite/templates/b7-pilot-input.json
```

`PilotService()` 无参，支持 `preflight(request)` 和 `report(request)`；独立模块 CLI 同样可用，见 [局部契约](../../personal-learning-suite/contracts/pilot-b7.md)。stdout 只输出元数据、引用和限制，不回显原答、教师参考或个人摘要。未配置模板 preflight 为 `needs_input`，report 返回四层 `not_executed`；主入口返回结果时退出 0，须读取 JSON 中实际状态，独立模块 preflight 未就绪退出 2。`can_start_automated=false` 与 `live_execution_status=not_enabled` 不随结构核查合格而改变。

2026-10-04 实际验证：[B7 专项](../../personal-learning-suite/validation/b7-pilot-runtime-report.json)通过 33 项，[完整回归](../../personal-learning-suite/validation/b7-all-runtime-report.json)通过 454 项，失败、错误及跳过均为 0；[原始输出](../../personal-learning-suite/validation/b7-all-runtime-output.txt)可逐项回查。[B0 静态核查](../../personal-learning-suite/validation/b7-b0-static-report.json)通过 32/32，19 份设计来源指纹未变。策略构建器 `--check` 确认 11 份资源一致，未重做外部研究核验。

[独立复核记录](../../personal-learning-suite/validation/b7-review.md)说明审查分工、初次 Windows CLI 编码失败及修复、四类漏拦截和五项修复重放；五项已计入 33/454 项，不能当新增学习样本。[演示](../../personal-learning-suite/validation/b7-demo-report.json)只用内存虚构对象，不建立个人学习空间。B10 软件覆盖见[本批索引](../../personal-learning-suite/validation/b7-b10-coverage.json)，十二个 `full_scenario_status` 仍为 `not_executed`；真实 V1—V4 同样均未执行。既有软件切片与 B7 真实试用分开，不因引用旧报告就升级为完整异常已验证。

## 从准备工具进入真实试用

用户之后需选择一门真实课程及近期片段，说明要完成的工作、允许资源和本次/近期可接受投入，选择套件外的个人记录目录与控制范围。系统据此整理有限目标、可检验判据、可靠材料/参考、实际承担者与短记录；不替用户把当前设计资料选为学习课程。

首期优先同课程一个可评审的复杂主产物，以及其中真实需要的后续使用和一项可及时结束的简单要求；这些覆盖可以由同一产物承担。只有简单目标可靠时可以有限启动，复杂整体与延迟未覆盖分别记录；主目标过大就保留深度和总体评审，只缩本次承诺。

内容、责任、有限预算和可控保存就绪后，才进入正常学习与目标内后续观察。用户已有充分支持就结束；不会制造错误、额外课程或无用途延迟检查来凑测试。最终用 V1—V4 分开的真实观察作限定的保留、调整、合并或延后决定；条件不足可以保持未知并结束本轮，真实学习收益与四角色净收益当前仍未验证。
