# B4 计划程序与承载边界

本文件说明虚构开发程序，从 SK05 主入口迁出技术提交规则；真实文件学习见 [SK05](../SKILL.md)与 [SK00](../../personal-learning/references/session-entry.md)。共同对象以 [共享契约](../../../../contracts/shared-contracts.md)为准，有限程序接口见 [planning-b4](../../../../contracts/planning-b4.md)，实现为 [learning_planning.py](../../../runtime/learning_planning.py)。当前程序只接受虚构开发记录，不绑定真实模型、课程或提醒宿主。

程序提交使用同一 SQLite、CAS 和 operation_id，恢复只用最新有效承诺及合法 checkpoint／原件。旧安排被替换时同事务处置受影响需求，不留并行有效安排。具体参数、授权、采用和错误码依 B4／B1 契约，不自行猜造。

保存失败不能称已安排；删除、暂停或用途限制发生后先重建合法范围，不从计划摘要或请求副本恢复证据。专业结果由各自责任采用，程序兼容不证明材料可靠、教学可执行或目标通过。

B5 虚构纵向集成与 B6 本地串行宿主已有实现，相关加载见 [纵向接口](../../personal-learning/references/vertical-workflow.md)、[宿主](../../personal-learning/references/network-host.md)。这不提供真实 AI 绑定、跨聊天输出拦截、身份认证、自动提醒或真实学习收益。

人工文件模式不套用上述事务声明，不要求用户先建程序授权或 JSON。当前入口顺序写入并读回；遇到部分失败分别报告，不把未确认的安排称为生效，也不另起一个权威安排库。
