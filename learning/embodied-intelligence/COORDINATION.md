# 任务与产物协调器：实际入口

2026-10-15正式备课运行器：新单元和实质回修使用[正常启动入口](../../personal-learning-suite/specs/preparation-runtime-start.md)的start-preparation，自动复用运行表、登记原聊天、保存任务计划和验证Python监听；成功后结束AG0当前轮，由程序等待与唤醒。接管失败明确处理，不以原生子Agent轮询代替。普通教学和人工查验仍沿下文原API；本数据库只登记本次明确接管的任务，不收编历史任务。

2026-10-14日常读取升级：current默认返回经原门禁核验的元数据，inputs/显式文本读取按覆盖标记续读；固定策略视图、manifest全清单校验和按用途/范围的desk见[日常指南](../../personal-learning-suite/specs/coordinator-agent-guide.md)。启动、等待和阶段收束见[有界执行](../../personal-learning-suite/specs/preparation-execution.md)。技术current的编码正文需显式`--view base64`，snapshot字节接口保持原契约。

2026-10-13。当前人工文件宿主已接入`tac-complete/0.1.0`；程序维护登记产物，AG0继续专业规划与最终采用。日常只需[简短操作指南](../../personal-learning-suite/specs/coordinator-agent-guide.md)和[日常程序](../../personal-learning-suite/scripts/coordinate_agents.py)，内部字段与恢复机制按需查[文件协作协议](../../personal-learning-suite/specs/coordinator-protocol.md)。

## 唯一状态来源

- 本目录`.coordinator/records.sqlite3`：已登记文件版本、任务、输入快照、依赖、审查/确认回执、按用途/范围采用的指针与本地事件。
- [state/control.md](state/control.md)：实际用户控制；[coordination/control.json](coordination/control.json)只是绑定原来源指纹的门禁投影，来源变化须重读并更新，不独立决定授权。
- [state/current.md](state/current.md)、[plan/current.md](plan/current.md)：学习事实、断点及安排，继续由原协议维护。协调器任务完成不等于学习发生。
- 原专业文件：完整正文与历史发生事实保留。正文中的生成时状态不当作当前协调指针。当前版本必须查程序，不另写可独立编辑的“当前采用表”。

## 角色实际调用

AG0登记专业任务、输入范围和是否审查；AG1/AG2通过begin开始并用inputs取得固定正文，完整另存新路径后deliver。AG3对确切任务结果开始审查并给opinion；AG0根据意见明确adopt。程序填状态号、指纹和指针，执行原有门禁；Agent仍决定专业结论、审查政策及变化是否相容。任务只报告running、submitted、blocked与实际产物/审查回执，未开始的任务给待开始动作；不填写百分比。do可一次提交明确意图，prepare/apply仅在需核对具体决定时选用，不新增用户审批。历史完整操作见[接入记录](coordination/integration-trace.json)。

从项目根取得当前角色的短状态：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_agents.py --workspace learning/embodied-intelligence --role AG0 desk
```

各执行上下文选择稳定consumer，开始、候选提交、审查返回、最终采用及等待恢复时取alerts，取得上下文后提交ack意图。事件不自动注入正在推理的模型；关键节点由程序再次校验。响应丢失先以原ticket查saved，不盲目刷新或重复决定。需要完整任务依据才inspect；初始化、原子安装文件、diff、receipt及recover保留在[技术入口](../../personal-learning-suite/scripts/coordinate_preparation.py)，不要求日常全量加载。

确实要等修订结果才用after_task；无关部分用已采用旧版，候选暂定必须写明确条件。草稿不能作正式输入，失败/超时保留旧采用版并明确交回AG0。受影响结果可保存候选，后续局部复核或修订由专业方决定。

原有未登记学习记录不全部迁库。普通原答保存、反馈和断点保持原协议；准备新单元及修改已登记专业产物进入协调入口。无工具时说明不能完成新协调提交，保留当前采用版和合法的无关工作。

## 本次接入边界

历史BC备课原件按明确对象版本和采用证据登记，不把最高文件名当有效版，不把历史兼容或局部审查记成新发生。前瞻试运行仅制作备课协作导航，专业确认/AG3功能均由本维护模型顺序兼任，不称独立复核。原备课充分性、用户能力和原教学断点不改，不启动授课、实验、外部消息或安装。

角色仍为可信本地操作员声明；文件协议不提供模型身份认证或恶意磁盘写入隔离。控制来源、指纹、SQLite事务和关键节点校验实际运行；共享专业语义仍由原契约和Agent职责维护。
