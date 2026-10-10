# 虚构运行接口

完整接口以 [strategies-b3c.md](../../../../contracts/strategies-b3c.md) 为准。Python [learning_strategies.py](../../../runtime/learning_strategies.py) 使用 B1 的同一 SQLite 和共享字段检查，且仅处理明确虚构开发工作区。

- `index` 返回轻量索引，不加载全卡正文、不推荐最优卡。
- `load` 返回指定已编译包的完整资源；未编译项返回回源位置和缺项，不能仅凭索引执行。

当前全部60张Encoding卡和4个Post包已编译，64个资源键均可load；索引的intended_work可按认知目标发现候选。返回executable=false表示还需实际任务适配和内容核验，不表示卡片不可读或需要申请编译。旧未编译分支保留供未来新增资源。
- `inspect` 接受当前虚构工作和候选 `MethodConfig`，检查精确引用、完整来源、必要条件、声明的关键操作／帮助、用途及预算范围。兼容只代表这些声明相容；不核内容真伪、实际泄题、有效教学或效果。
- `reuse` 读取显式采用且仍为当前修订的已存配置，复验当前 context；成功为 reusable，并不启动教学或产生新事件。
- `submit` 每次提交一个 MethodConfig，在显式授权与采用下复用 `LearningStore.commit` 的 CAS、幂等、当前控制和删除门禁；检查返回不自动采用。不夹带原件、活动、表现、判断、计划或 WorkResult。
- `change` 接收已存 MethodConfig 的精确 changed_refs、resource_keys 或 resource_changes；资源键／来源变化仅按已存 selected_parts／source_refs 定位配置，再追踪已记录 ObjectRef 依赖。明确指定限制选项时调用 B1 限制接口；历史和当前专业结论不被自动重写，限制不被自动恢复。

从套件目录运行 `python src/runtime/learning_strategies.py index --work <导航词>` 或 `load --resource-key <资源键>`；inspect／reuse／submit／change 使用 `--workspace <虚构工作区>` 与 `--request <UTF-8 JSON>`，change 的持久限制还须 `--restrict`。index 是文本过滤，不是最优匹配。load 返回 executable=false，因为完整包仍待当前任务适配与内容核验；未编译返回 needs_source_review。

自然请求先按 [具体工作导航](selection-adaptation.md) 发现候选，再用原 ID／资源键定位；零文本命中不证明无适用方法。人工教学可以按该页回读未编译原卡、核验学科内容并实例化，开发程序仍不能把它当已编译包提交。`load` 的完整 Post 返回含源正文；只取 `name` 或顶层摘要仍未完成专业阅读。

`inspect` 即使声明部分借用，也会核所选包针对当前用途的全部必要条件。人工教学的工作裁剪不自动成为程序支持的条件裁剪；不适用条件不能伪填满足。简单恢复或未编译方法可沿合法人工路径继续，是否补相称的开发资源另行维护，不改变真实教学目标以迁就声明检查。

无课程或执行授权时只交候选，不暗建会话。出现冲突先重读有效状态；保存失败保持待保存，不重新造一次操作。未知时间、帮助和接触必须用 Fact 表达，不补成零值／无帮助。CLI 输入文件及 stdout 是调用方副本，SQLite 删除不覆盖这些外部副本；不要放入真实个人数据。

本批只证明资源、声明与受控保存的有限软件行为。SK06 的实际选法价值、真实课程、宿主身份与输出边界留后续验证；程序不替代读正文、专业采用和相应内容／证据核查。

接口输入版本为 `pl-strategies-input/0.2.0`，通用资源仍为 `pl-strategies/0.1.0`。依 [B3 互通契约](../../../../contracts/b3-interop.md)，`context.material_context` 须提供完整 B2b 用途绑定并纳入配置审查绑定；仅有 supported 标签不能替代用途检查。已采用配置通过 B3b 执行请求传入，避免活动与配置互相升级修订。旧配置缺这项审查绑定时须 AG1 复查后形成新修订，不改写旧配置或旧事件。
