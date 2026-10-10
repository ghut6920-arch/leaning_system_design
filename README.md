# AI 个人学习系统：项目导航

本目录将运行套件、设计研究、演示数据与维护记录分开。需要使用或修改 Agent／Skill 时，从 `personal-learning-suite` 开始；需要理解设计依据时，从 `docs` 开始。

开始／继续具身智能学习可直接复制 [启动提示词](learning/embodied-intelligence/START_PROMPT.md)。当前公开指令与导航已按 [重构路线](docs/implementation/AI个人学习系统_教学内容重构执行路线_v1.md)推进到第六阶段。最新的全套来源比较、新上下文审查及局部修复见 [原意复审](docs/audits/AI个人学习系统_全套Skill与Agent原意复审_2026-10-05.md)，第六阶段当时的修改与验证保留在 [历史记录](docs/implementation/AI个人学习系统_教学内容重构_第六阶段实施与验证_2026-10-05.md)。程序和虚构首回合核查不替代真实学习效果。

## 去哪里找什么

| 内容 | 入口 | 用途 |
|---|---|---|
| 实际 Agent、Skill、运行程序 | [实现入口](personal-learning-suite/src/README.md) | 四份 Agent 定义、七个 Skill 开发包、Python 运行实现 |
| 套件说明与开发命令 | [套件 README](personal-learning-suite/README.md) | 当前能力、B0—B7 历史与本轮修复状态 |
| 共享契约 | [shared-contracts](personal-learning-suite/contracts/shared-contracts.md) | 对象、责任、授权、交接与唯一字段维护源 |
| 运行资源 | [资源说明](personal-learning-suite/resources/README.md) | 来源登记、实际策略资源与依赖状态 |
| 架构、方案、研究、提示词、审阅和交付报告 | [文档分类索引](docs/README.md) | 57 份原顶层文档，按八类保存 |
| 真实具身智能学习（人工文件模式） | [学习入口](learning/embodied-intelligence/README.md) | 已导入课程大纲；跨模型入口、原答、实验与恢复记录 |
| 虚构演示数据库 | [演示说明](examples/README.md) | 10 个开发演示空间；已有历史保持，不导入真实个人记录 |
| 目录移动与原始备份 | [维护说明](maintenance/README.md) | 路径映射、原始 ZIP、指纹变化及整理验证 |

## 当前目录

```text
学习系统架构设计/
  README.md
  personal-learning-suite/
    src/agents/       实际 Agent 定义
    src/skills/       实际 Skill 开发包及随包引用
    src/runtime/      运行实现
    contracts/        共用与专业接口
    resources/        运行资源及来源登记
    templates/        输入模板
    specs/            开发规格与验收方案
    fixtures/         虚构测试输入
    tests/            自动化测试
    scripts/          检查、演示、资源构建与维护脚本
    validation/       测试结果、审计反例与历史证据
  docs/
    architecture/     总体架构与实施路线
    designs/          工作包设计方案与交接
    research/         研究报告、证据台账、微操作与研究策略库
    prompts/          架构与工作包设计提示词
    analysis/         顶层设计分析
    reviews/          设计审阅及检查记录
    implementation/   B0—B7 交付与接口修复报告
    audits/           综合审计及修复实施记录
  learning/embodied-intelligence/  真实学习文件工作区与通用模型入口
  examples/workspaces/ 虚构演示数据库
  maintenance/         整理清单、备份与验证
```

`src/agents` 和 `src/skills` 是已有实现；`specs/skills` 是开发规格，两者用途不同。`docs/research/04_Encoding策略库.json` 是研究源；实际加载的精简资源在 `personal-learning-suite/resources/strategies`，由构建器转译并核对来源。

## 建议阅读顺序

1. [整体流程与概念架构 v1](docs/architecture/AI个人学习系统_整体学习流程与概念架构_v1.md)。
2. [Agent 与 Skill 工作网络及实施路线](docs/architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)。
3. [实际实现入口](personal-learning-suite/src/README.md)。
4. [修复实施记录与当前能力](docs/audits/AI个人学习系统_架构审计修复实施记录_2026-10-04.md)。

七个 Skill 仍是依赖当前套件布局的开发包，未安装为自包含发布包。程序中的真实模型教学、课程及个人记录承载尚未绑定；虚构数据库不能直接作为真实个人学习空间使用。具身智能已另建人工文件学习工作区，引用同一框架，尚未绑定正式运行程序。

目录整理没有改教学算法或学习者历史。源文件中的路径引用已更新，对应来源指纹与派生资源重新生成；原始文件及旧来源登记可在维护备份中回查。历史 JSON/TXT 的实际执行路径保留原值，旧路径的新位置由移动清单查找。
