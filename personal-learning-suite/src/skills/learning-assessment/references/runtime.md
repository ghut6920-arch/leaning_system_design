# B3a 评估辅助器与 B3 互通

本文件仅说明虚构开发程序，从 SK04 主入口迁出技术调用规则；真实文件学习见 [SK04](../SKILL.md)与 [SK00](../../personal-learning/references/session-entry.md)。共同语义来自 [共享契约](../../../../contracts/shared-contracts.md)，局部接口见 [assessment-b3a](../../../../contracts/assessment-b3a.md)，实现为 [learning_assessment.py](../../../runtime/learning_assessment.py)。程序及 B1 只接受虚构开发记录，真实原答不能改标 synthetic 进入。

## 调用与有限保障

`AssessmentService.inspect_judgment(judgment, context)`、`inspect_diagnostic(note, context)` 只读；`submit_assessment(request)` 检查后经 B1 受控提交。CLI 为 `inspect/diagnose/submit`。用协议规定的操作级评分、选定响应点、时间线完整声明和精确时间表示，不猜造缺字段；模型先回原答评分，程序不自动理解学科真伪。

`compatible` 只说明声明相容，时间线完整或材料核验声明不证明真实无帮助或正确性，检查通过不等于判断已采用。角色名、`review` 模式或虚构授权不能证明真实身份、重要复核资格、独立性或已启动 Agent。

读取／提交都先查控制，状态冲突重读，失败保持待保存，不能绕过 B1 保存入口。纠错的材料用途、历史判断、实际误导、计划需求分别恢复；合法原答足够时直接重评。删除后仅以剩余合法依据保留／收窄／撤销，不从摘要或迟到载荷复活原答。请求文件、stdout 等调用者副本不在 SQLite 删除范围，按实际控制范围报告。

## 跨包引用

程序跨包评价遵守 [B3 互通契约](../../../../contracts/b3-interop.md)：使用保存回执的精确事件与响应序号，完整材料用途通过 `context.material_context` 传入；判断用途与材料用途分别检查。父事件帮助沿原始精确引用继承，延迟从相关操作的最近实际接触计算，修订时间未知不得回退初答时间。历史配置不因新版新增依赖自动失效。

这些技术字段不成为人工文件反馈的门槛；人工仍须保留真实原件、版本、帮助和相关时间，不能因无需程序序号而省略影响结论的条件。
