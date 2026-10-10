# AI 个人学习系统：B1 保存与入口骨架 v0

日期：2026-10-03。承接[实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第十二节 B1 及[B0 基线](AI个人学习系统_B0规范与资源基线_v0.md)。

状态：B1 已完成。已交付共享记录组件、SK00 开发态入口和 AG0 运行外壳，虚构记录可保存、重新打开读取、恢复定位、限制、清理和限定导出。33 项实际行为测试通过；系统仍处于开发阶段，尚未执行真实课程教学或部署四个 Agent。

## 本批交付

| B1 要求 | 实际实现 | 证据与边界 |
|---|---|---|
| 一个共享规范来源 | [learning_store.py](../../personal-learning-suite/src/runtime/learning_store.py)：一个 SQLite 数据库保存对象修订、当前指针、原件、控制、回执和状态修订 | 保存后新建适配器仍可读取；没有各 Skill 的独立记录库 |
| 旧状态提交不覆盖 | 串行事务、状态修订 CAS、操作标识去重、失败回滚 | 两个实际连接争同一修订仅一个成功；同操作不同载荷拒绝 |
| 原件和历史可追溯 | [contract_rules.py](../../personal-learning-suite/src/runtime/contract_rules.py)读取唯一[共享契约](../../personal-learning-suite/contracts/shared-contracts.md)；精确引用旧修订和原件定位 | 原件逻辑路径不可覆写，当前适配仅支持 ArtifactRef revision=1；新原件用新路径 |
| 虚构事件可限制和清理 | 用户暂停、专业用途限制、持久停用门、正文与依赖清理、关联索引删除、迟到拒绝 | 删除清理失败后重启仍受限；独立对象与名称相近的无关原件保留 |
| SK00 开始／恢复／路由 | [开发态 SKILL.md](../../personal-learning-suite/src/skills/personal-learning/SKILL.md)和[personal_learning.py](../../personal-learning-suite/src/runtime/personal_learning.py) | 只检查条件、定位断点、返回专业候选去向；没有补测、改判、正式委派或教学 |
| AG0 控制外壳 | CLI 支持 init、status、start、resume、route、pause、restrict、delete、export、integrity | 默认恢复只读；显式解除用户暂停不解除专业限制 |

本批承载协议为 `pl-store/0.1.0`，共用语义仍为 `pl-contracts/0.1.0`。SQLite 是保持原契约的本地实现选择，具体事务、引用和删除边界见[B1 承载接口](../../personal-learning-suite/contracts/runtime-b1.md)。`entry_actor` 是开发测试配置，不能视为真实身份认证。

## 实际检查与演示

[行为报告](../../personal-learning-suite/validation/b1-runtime-report.json)与[原始测试输出](../../personal-learning-suite/validation/b1-runtime-output.txt)记录 33 项通过、0 失败、0 错误、0 跳过。宿主为 Windows 11、CPython 3.12.3、SQLite 3.46.1。测试使用隔离临时目录和人工夹具，覆盖保存重读、修订冲突、幂等、角色与授权拒绝、候选采用拒绝、暂停／专业限制、删除全历史及派生内容、关联索引、迟到拒绝、失败后的持久停用、原件路径边界、导出和恢复未知。

B0 静态复验仍为 32 项通过，19 份登记来源指纹与定位一致，本地链接无缺失；[静态报告](../../personal-learning-suite/validation/b0-static-report.json)保留检查输出。开发态 SK00 通过 skill-creator 的结构校验；演示脚本在新临时空间保存后再次运行仍为修订 1、26 个对象，未重复导入。

独立前向试用使用请求：“接着上次未完成的完整推理，不过今天先只告诉我从哪里继续、哪些条件还没确定；我想看原答再决定。”入口找到既有断点、同一父产物和原答定位；说明唯一当前承诺与执行授权缺失，未记录动作与帮助保持未知。查看前后状态修订均为 1，26 个对象保持一致，没有新增教学、补测或计划。详见[核查记录](../../personal-learning-suite/validation/b1-review.md)。

项目根下已建立明确标记的[B1 虚构演示学习空间](../../examples/workspaces/B1_虚构演示学习空间/records.sqlite3)，保存 26 个虚构对象和 1 份虚构原件。重新打开读取与完整性检查均为 `ok`；恢复为 `needs_input`，评分路由为 `candidate/not_ready`，`teaching=false`，未创建工作单。精简结果见[演示报告](../../personal-learning-suite/validation/b1-demo-report.json)。

从项目根运行：

```powershell
python personal-learning-suite/scripts/check_b1.py
python personal-learning-suite/scripts/check_b0.py --report validation/b0-static-report.json
python personal-learning-suite/scripts/demo_b1.py --workspace examples/workspaces/B1_虚构演示学习空间 --report validation/b1-demo-report.json
python personal-learning-suite/src/runtime/personal_learning.py --workspace examples/workspaces/B1_虚构演示学习空间 resume --activity-id FIX-activity
```

演示脚本仅在初始空空间装入本项目人工夹具；已有空间只查看，不重填已删除数据。`init` 本身只建空空间，不生成课程或个人事实。B0 历史夹具仍用 `synthetic=true`，脚本确认后在内存补入导入 API 要求的 `synthetic_only=true`。

## 仍保留的边界

- B1 只接收虚构开发记录。真实课程、个人保存范围、预算、模型和宿主绑定仍未确定；[依赖清单](../../personal-learning-suite/resources/runtime-dependencies.json)继续保留这些未知。
- 开发态 SK00 依赖当前项目布局，尚未安装，也不是自包含发布包。SK01—SK06 的专业执行、教学、评分、计划与策略选择留后续批次。
- 删除成功通常涉及停用与清理两次状态修订；清理失败也可能已保存停用门，应重读状态再继续。受控数据库之外的历史、备份、外部副本与已加载 Agent 上下文未由程序清除。
- 导出包含所选对象的引用依赖，原件以整份逻辑文件提供。查看原答时按定位展示请求片段；B1 没有原件片段裁剪接口。
- 33 项测试只验证明列的 B1 切片。B10 全情境、宿主接管／旧输出拦截及 V1—V4 未验证；数据库事务串行化不能证明多 Agent 展示隔离。策略运行索引、卡包与 Post 方法说明仍待 B3c。

下一批可依据稳定契约并行推进 B2a 的 SK01 目标设计与 B2b 的 SK02 材料准备；真实目标与可靠材料仍需互核。B0 的来源原文、历史验收结论和未执行全情境保留。
