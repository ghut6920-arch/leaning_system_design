# 全套原意复审：产物与证据范围

日期：2026-10-05。正式结论见[全套原意复审](../../../docs/audits/AI个人学习系统_全套Skill与Agent原意复审_2026-10-05.md)。当前目录只保存公开来源审查、虚构案例和维护检查，真实课程文件没有复制到这里。

## 来源核对和实际首段

| 分工 | 原文比较与覆盖 | 已生成内容 |
|---|---|---|
| 入口／计划／角色 | [报告](reviewers/entry-continuity-fresh/audit-report.md)、[覆盖](reviewers/entry-continuity-fresh/source-coverage.md) | 四个独立文件：陌生纯讲解、跨模型只收束、原答评分异议、看完整参考与换文字；请求／首段／有限索引分段保留 |
| 目标／材料／评价 | [报告](reviewers/design-assessment-fresh/audit.md)、[覆盖](reviewers/design-assessment-fresh/coverage.md) | [请求示例](reviewers/design-assessment-fresh/requests/R1-projection-proof.md)、[实际输出示例](reviewers/design-assessment-fresh/outputs/R1-projection-review.md)、[完整产物清单](reviewers/design-assessment-fresh/manifest.json) |
| 教学／策略 | [报告](reviewers/teaching-forward-fresh/fresh-validation-report.md)、[覆盖](reviewers/teaching-forward-fresh/coverage.json) | [原始请求](teaching-forward-requests.json)、T1—T4首回合、生成冻结清单及核源后的不变检查 |

主审逐项内容复核见[root-content-review](root-content-review.md)，跨包衔接、旧审阅与研究优先范围见[integration-source-review](integration-source-review.md)。审查者原始产物按显式临时目录复制，清单见[review-artifacts](review-artifacts.json)。原始输出／清单保留当时执行路径，不将改写后的展示稿冒充原输出；[持久保存的R3图](reviewers/design-assessment-fresh/artifacts/R3-affine-comparison.png)与代码锚点在本目录可回查。

主审补读研究的准确范围和团队合并阅读边界见[research-source-completion](research-source-completion.md)。正式专项补读保存在各执行者的source-completion.md，原覆盖清单保持其初次核查时的实际范围。

三位新执行上下文没有取得旧审计结论或理想答案，教学首段在核原设计／研究之前冻结；其他两组先核对应来源后实演。所有执行者仍是同系统模型子Agent，生成后的自查不能当独立评分或真人观察，主审复核也不是盲评。审查目录不是技术访问隔离。原件／答案均为虚构输入，没有续造学习者答复或写入个人课程。

## 维护检查

- [七Skill格式](skill-format-results.json)：结构检查，不判断教学质量。
- [B0静态](b0-static-result.json)：32项、19来源、角色／Skill规格；未来15情境保持not_executed。
- [资源构建check](resource-check-observation.json)：11文件、60索引、3编译Encoding包、4Post包，未重查外部论文。
- [公共完整性](integrity-result.json)：链接、清单、来源和冻结文件；不支持学习效果。
- [学习目录末段核查](learning-unchanged.json)：仅核最后验证时段；前段RAM守护进程续接后不可用，未取得全程结果。只保存总数与变化总数，不保存私有路径、内容或指纹；此次Agent写入范围没有个人学习文件。
- [本轮汇总](verification-summary.json)：执行范围与未验证项。

`before.zip`只含48个允许审查修改的既有公开文件；`before.json`只记录公共文件版本。485个其他既有公共文件与19来源被冻结核查。精确既有改动见[public-changes.diff](public-changes.diff)和[changed-public-files](changed-public-files.json)。原研究、历史报告、运行实现与个人学习记录不在本次修复范围内。

本轮V1限具体内容锚点，V2限12个实际首段；V3真实学习、V4可比投入／收益未执行，后续反馈和实际状态提交不能从这些文件推断。
