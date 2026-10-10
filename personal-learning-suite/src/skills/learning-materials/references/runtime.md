# B2b 运行接口与边界

本文件只说明 B2b 虚构开发程序；[SK02](../SKILL.md)和 [AG2 角色](../../../agents/AG2-materials.md)也支持按课程协议开展人工文件工作，不以此程序作为前置。唯一共用对象源为 [共享契约](../../../../contracts/shared-contracts.md)；程序承载沿用 [B1](../../../../contracts/runtime-b1.md)，材料局部协议由 [materials-b2b.md](../../../../contracts/materials-b2b.md) 维护。运行辅助器在 [learning_materials.py](../../../runtime/learning_materials.py)，使用相同 `records.sqlite3`，不另建材料库、手写对象 schema 或独立有效状态。以下调用、授权对象和事务说明只对程序模式成立，不能套用到真实文件记录。

## 实际调用

通过 `MaterialsService(store)` 进行 `read_fragment(request)`、`inspect_material(material, context, incoming=None)`、`submit_material(request)`、`trace_change(request)`；命令行提供 `read/inspect/submit/change`。CLI 从 UTF-8 JSON 请求文件读取载荷，格式和字段用局部协议；下面使用占位路径：

```text
python personal-learning-suite/src/runtime/learning_materials.py --help
python personal-learning-suite/src/runtime/learning_materials.py --workspace <虚构开发记录目录> --request <读取请求.json> read
python personal-learning-suite/src/runtime/learning_materials.py --workspace <虚构开发记录目录> --request <材料与当前用途.json> inspect
python personal-learning-suite/src/runtime/learning_materials.py --workspace <虚构开发记录目录> --request <受控材料提交.json> submit
python personal-learning-suite/src/runtime/learning_materials.py --workspace <虚构开发记录目录> --request <更正范围.json> change
```

| 操作 | 支持的有限工作 | 专业责任仍须完成的工作 |
|---|---|---|
| read | 通过共享组件读取许可原件片段并返回实际可读取范围 | 核含义、缺模态和必要前后文；读取成功不能冒充内容核验 |
| inspect | 核对材料引用、核验声明、目标操作／潜在帮助与用途条件 | 依据原文、推导／测试作内容结论；检查图像或交互成品；人工检查标题／配色等实质泄露 |
| submit | 经当前控制、显式授权、采用、CAS 与幂等检查提交材料对象 | 提交前完成必要专业核验；prepared 不记作展示、活动或学习成绩 |
| change | 从合法实际引用追踪疑误影响并形成回查输入；显式加 `--restrict` 时先调用共享限制 API 建立持久门禁 | 裁定错误／更正，补未知依赖；不同责任分别处理四个恢复面 |

所有写入携带明确 `expected_state_revision`、`operation_id` 与协议要求的授权／采用；实际字段和错误码以共享组件与材料协议为准，不自行补猜。`conflict` 重读后重新决定，`rejected` 返回缺项，`not_saved` 保持待保存。幂等回执不许可再次使用当前已删除／受限依据。

`read` 返回候选读取事实，内容／主张待核且未保存；`compatible` 仅说明本切片的引用和声明相容。`submit` 的正常用途材料只接受 compatible，partial／pending／error 保持受限候选，不由本助手落盘；单独读取事实可在专业授权及采用检查后保存。`change` 默认只读，四恢复返回 pending，不解除专业限制或改写历史判断。请求文件和 stdout 为调用者副本，不在 SQLite 删除范围。

只按请求定位读取合法片段，避免为了一个初答或题干将整份含教师参考的原件显示给用户。删除与专业限制通过当前受控组件，不绕行直接查询数据库或文件恢复历史。工作区原件路径是 SQLite 内逻辑定位；真实宿主文件读取／身份绑定不由该逻辑路径实现。

## 加载与限制

通常加载 SKILL、本次模式规则、当前领域／对象规则、精确来源与用途相关目标／活动。复杂整体参考按需读全必要部分；内容争议回原件／推导／测试和直接依赖，研究主张争议才加载 R01／R05／R06 对应条目。其余研究和卡库不是常驻上下文。

当前仍使用虚构开发记录与 `verified_for_fixture` 绑定；`entry_actor=AG2` 不认证真实身份。未绑定 PDF/OCR、多模态查看、真实专业核验工具、自动 Agent 接责、旧输出拦截或后台展示。可读原件、用途检查和事务行为的测试不证明数学／代码／现实事实本身已核验，不证明真实 V1—V4 或学习收益。

用户直接调用但无执行授权时可读合法范围、做候选分析，不能正式写入。后台默认只回专业结果；教学入口 AG0 按当前条件采用并记录实际展示。宿主不能隔离并行输出时单入口顺序运行，接管不能只靠角色文件或 execution_epoch 声称旧 Agent 已停。
