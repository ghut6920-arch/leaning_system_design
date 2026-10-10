# 具身智能学习工作区

这里保存你的真实学习资料与过程，方向为 World Model、WAM、VLA 和生成式策略。创建于 2026-10-04。实际学习位置、是否开始与已有支持以 [当前状态](state/current.md)及其合法原件为准，本导航不维护第二份学习状态。

## 从哪里开始

完整启动与跨模型恢复可直接复制 [START_PROMPT.md](START_PROMPT.md)。下面是简短入口。

将下面这段话发给有文件访问能力的模型。推荐打开整个“学习系统架构设计”项目，让它能读取共享框架。

```text
请读取 learning/embodied-intelligence/MODEL_ENTRY.md，按其中的通用文件协议接入现有 Agent 与 Skill 框架。先核对状态和恢复点，再开始或继续具身智能学习。用已有资料或我的作答判断起点，不预设我已经掌握或完全不会。只补影响当前起点的信息。保存实际题面、原答、帮助、修订与停止点；说明本次角色是否由同一模型兼任。
本次可用时间：我将在开始时提供。
```

也可以直接说“读取这个目录的 MODEL_ENTRY.md，开始学习”或“继续上次学习”。没有文件工具的模型需收到入口、规则及当前合法记录，并返回待保存文档，由你或有文件能力的工具保存；它不能声称已经写入。

## 文件去向

| 内容 | 入口 |
|---|---|
| 任意模型的接入与操作流程 | [MODEL_ENTRY.md](MODEL_ENTRY.md) |
| 四个 Agent、七个 Skill 的原始规则定位 | [FRAMEWORK.md](FRAMEWORK.md) |
| 当前状态与用户控制 | [当前状态](state/current.md)、[控制范围](state/control.md) |
| 原始大纲与课程地图 | [导入原件](course/original-syllabus.md)、[课程地图](course/course-map.md) |
| 来源与核验状态 | [来源登记](materials/sources.md) |
| 候选目标与阶段验收 | [课程目标候选](goals/course-goals-draft.md) |
| M0–M8 学习位置 | [模块索引](modules/README.md) |
| 活动问题、备用帮助与教师参考 | [问题组织](questions/README.md) |
| 会话、原答、帮助与修订 | [会话记录](sessions/README.md) |
| 全部学习代码（用户、AI 或共同编写） | [统一代码目录](code/README.md) |
| 推导、报告与实验记录 | [学习产物](artifacts/README.md)、[实验](experiments/README.md) |
| 条件化评价、待复核项 | [评价记录](assessment/README.md) |
| 当前安排与唯一需求队列 | [当前计划](plan/current.md)、[需求队列](plan/needs.md) |
| 通用记录模板 | [模板说明](templates/README.md) |

本目录采用人工文件协议，明确请求开始／继续后可按实际授权开展教学并保存；已有 Python／SQLite 仍只用于虚构开发记录，人工学习不需要先取得程序授权对象。模型可顺序兼任四职责；文件指导不等于平台 Skill 安装、多 Agent 启动、身份／权限绑定或聊天拦截，接入能力据实际宿主报告。
