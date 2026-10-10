# AI 个人学习系统：B3a 证据评估与 AG3 职能 v0

2026-10-03 联合接口更新：已统一资格，按实际允许资源、父帮助、所选响应之前的最近相关练习／帮助检查，并分开材料与判断用途。当前 B3a 82 项检查通过，见 [联合评估与修复](AI个人学习系统_B3联合接口评估与修复_v0.md)；本文件下列原批报告保留首次交付结果，不改写旧事件或判断。

日期：2026-10-03。承接[实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第十二节 B3a，沿用 B0/B1/B2a/B2b 的共享对象、目标、材料与保存接口。

状态：B3a 有限开发切片已实现。交付 `learning-assessment`、AG3 完整开发态角色、常规评分授权模板、证据／诊断检查与受控提交、虚构测试和演示。Skill 尚未安装，AG3 尚未绑定真实宿主；程序不自动判断任意学科答案真伪。

## 交付与行为

| 内容 | 落点 | 实际作用 |
|---|---|---|
| SK04 及精简规则 | [Skill](../../personal-learning-suite/src/skills/learning-assessment/SKILL.md)、证据规则、诊断与复核 | 从原任务、原答、实际帮助和先定判据作条件化判断；当前充分即可结束 |
| AG3 专业边界 | [角色](../../personal-learning-suite/src/agents/AG3-assessment.md) | 重要复核、有限诊断、评分争议和常规授权；不直接排复习或改正式目标 |
| 操作与条件检查 | [AssessmentService](../../personal-learning-suite/src/runtime/learning_assessment.py)、[接口](../../personal-learning-suite/contracts/assessment-b3a.md) | 指定响应点、操作级帮助、任务资格、双轴、目标内时间、相反评分与精确依据 |
| 常规评分授权 | [模板](../../personal-learning-suite/templates/routine-scoring-grant.json) | 对象、判据、结论、升级信号和共享预算；unbound 模板不能作为有效授权 |
| 同一保存入口 | inspect / diagnose / submit | 检查只读；提交沿 B1 CAS、幂等、权限与采用门；不新增事件、补测、需求或计划 |
| 实际验证 | [验收](../../personal-learning-suite/specs/b3a-acceptance.md)、[行为报告](../../personal-learning-suite/validation/b3a-runtime-report.json)、[收口记录](../../personal-learning-suite/validation/b3a-review.md) | 人工夹具、隔离空间及独立 Skill 前向；不成立完整 B10 或真实 V1—V4 |

共用协议保持 `pl-contracts/0.1.0`，承载保持 `pl-store/0.1.0`；评估适配为 `pl-assessment/0.1.0`。没有增加数据库、全章 mastered 状态或新的复习队列。原设计／研究文档与既有历史验证报告保留。

帮助前原答可以保留独立支持；帮助后的修订只限制被代做操作，其他工作与有帮助条件下的支持仍保留。同题修订、多次评分和跨要求引用不增加样本。支持、使用资格和专业采用分别保存，当前日历过去不证明延迟保持。

`compatible` 只表示给定声明、引用与条件相容。模型仍需回实际原件并核专业评分理由；完整性、材料核验及 active 授权都是人工声明，不能证明真实无提示或真实身份。递归旧材料／来源、专业限制和删除保持当前门，不能用重评宣称它们已恢复。

## 可执行验证和虚构演示

从项目根运行：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b3a.py
python -X utf8 personal-learning-suite/scripts/demo_b3a.py --workspace "examples/workspaces/B3a_虚构证据学习空间"
python -X utf8 personal-learning-suite/src/runtime/learning_assessment.py --help
```

演示首次建立独立人工空间，提交一份候选判断，再重新打开读取；已有空间只读，不重导入已删除内容。结果见[演示报告](../../personal-learning-suite/validation/b3a-demo-report.json)。没有自动采用、教学、补测或计划变更。调用者请求文件、stdout、报告和上下文副本不属于 SQLite 删除范围。

实际验证：B3a 54 项行为测试通过；B1/B2a/B2b 回归分别为 33/42/30 项通过；B0 32 项静态用例及 19 个来源检查通过，本地链接无缺失。原始输出和独立前向结果见收口记录。这些结果只证明人工开发切片。

已具备评估开发接口，可供共同教学核心接入；真实课程、合法原答、预算、角色模型、宿主身份／输出边界、专业限制恢复和真实效果仍须按后续阶段验证。
