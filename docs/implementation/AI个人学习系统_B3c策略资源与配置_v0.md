# AI 个人学习系统：B3c 策略资源与配置 v0

2026-10-03 联合接口更新：当前配置输入为 `pl-strategies-input/0.2.0`，材料完整用途绑定进入审查，配置已可显式交给 B3b 并沿响应点连接 B3a。详见 [联合评估与修复](AI个人学习系统_B3联合接口评估与修复_v0.md)。下列首次交付报告保留原结果；通用资源仍为 0.1.0，旧配置用于新执行前须重核，不改写旧演示空间。

日期：2026-10-03。承接[实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第七／十二节、D07 策略使用规则及 D04—D06 专项边界；沿用 B0／B1 共享对象和保存入口，并参考 B2a／B2b 的有限开发交付。

状态：B3c 有限开发切片已实现，通过虚构软件验收。交付 SK06 `learning-strategies`、60 卡轻索引、三张完整 Encoding 卡包、四份 Post 方法说明、配置检查／复用／共享提交和已记录依赖追踪。Skill 未安装，真实角色与课程未绑定，未执行真实教学、论文外部核验或学习效果验证。

## 本批交付与边界

| 要求 | 实际交付 | 能证明什么 |
|---|---|---|
| SK06 最小选法／适配 | [SKILL.md](../../personal-learning-suite/src/skills/learning-strategies/SKILL.md) 与选法、维护、运行参考 | 对准当前工作，保留前置、借用范围、替代差异和停止；已有可靠活动无需遍历库 |
| R03 轻索引 | [strategy-index.json](../../personal-learning-suite/resources/strategies/strategy-index.json) | 60 个 Encoding 原 ID 与四个套件新增 Post 键可定位；compiled 不等当前课程准入 |
| R02 共用约束与少量卡包 | [S07](../../personal-learning-suite/resources/strategies/encoding/S07.json)、[X02](../../personal-learning-suite/resources/strategies/encoding/X02.json)、[R09](../../personal-learning-suite/resources/strategies/encoding/R09.json) | 完整 R03 正文、R02 同卡正文、文首文尾规则、正式方案覆盖及证据边界；其余 57 卡只导航 |
| Post 方法导航 | [资源说明](../../personal-learning-suite/resources/strategies/README.md) 与 retrieve-relation／select-method／conditional-update／retrieve-generate-order 四包 | 有具体 D06／R04／R05／R06 定位和完整必要摘录；不伪造原 Post 卡号、不固定检索在先 |
| 版本与转译核对 | [构建脚本](../../personal-learning-suite/scripts/build_b3c_resources.py) 与 [manifest](../../personal-learning-suite/resources/strategies/manifest.json) | 11 份输入来源的原文件指纹及正文定位，可复现 11 个产物；指纹不证明内容或效果 |
| 配置、采用与保存 | [StrategiesService](../../personal-learning-suite/src/runtime/learning_strategies.py)、[局部接口](../../personal-learning-suite/contracts/strategies-b3c.md) | 条件／版本／当前引用声明检查与正式采用分开；MethodConfig 沿 B1 保存，未新建数据库 |
| 失配与版本变化 | `change` 与显式 `change --restrict` | 根据已存 selected_parts／source_refs 定位配置，再追踪 ObjectRef；用途门持久保存，历史事件不改写，各恢复责任保持待处理 |

共用协议保持 `pl-contracts/0.1.0`，保存承载保持 `pl-store/0.1.0`，资源修订为 `pl-strategies/0.1.0`，局部输入适配为 `pl-strategies-input/0.1.0`。公共必填字段仍只维护于共享契约，嵌套检查单列在 B3c 接口。原设计／研究文件和来源登记未修改。

R02／R03 是同一卡库的两个载体，不算两份独立证据；S07＋X02 可以只借同一补全的一部分，不产生两次表现或强制追加完整卡片训练。R09 的空 `evidence_ids` 与设计综合性质保留，不补造论文、不因空引用自动禁用；所选包来源只允许登记并集。Post 的 E01—E49 仅是文献号，D06 的 P1—P5 仅是验收覆盖号。

`compatible` 表示当前声明、完整资源、版本与受控引用满足有限检查，不证明学科内容正确、隐藏线索已识别、反馈实际发生、延迟已经合格或方法有效。`reviewed` 不等采用；正式配置要显式 AG1 采用、已有授权和 B1 事务门。`reuse` 复验已存且采用的当前配置；合法 `previous_config` 保留精确历史，旧修订不能伪装当前配置。

独立用途按当前活动判据定位目标时间范围，不能通过 `requires_time_condition=false` 隐去适用时间要求，也不能给 `not_required` 目标制造必需延迟。软件只检查范围及条件声明，实际时序／接触资格交 SK04；教学用途可继续当前建构。必要前提、反馈、预算可行性或当前独立条件未知时返回受限，阶段成本未知仍保留未知，不补造分钟数。

## 实际验证

[B3c 行为报告](../../personal-learning-suite/validation/b3c-runtime-report.json)与[原始输出](../../personal-learning-suite/validation/b3c-runtime-output.txt)记录 **44 项通过，0 失败、0 错误、0 跳过**。隔离临时空间内的课程、材料、预算、授权、采用及原答均来自人工虚构夹具。覆盖轻索引与未编译拒绝、完整正文／共用约束、资源／来源变更、R09 证据边界、可靠活动短路、单一补全组合、必要未知、反馈与预算、帮助代做、目标时间范围、专业采用、保存重开、CAS／幂等、暂停限制、删除迟到、历史配置、源版本追踪及真实 CLI 子进程的持久限制。

回归结果分别保存为 [B1：33 项](../../personal-learning-suite/validation/b3c-b1-regression-report.json)、[B2a：42 项](../../personal-learning-suite/validation/b3c-b2a-regression-report.json)、[B2b：30 项](../../personal-learning-suite/validation/b3c-b2b-regression-report.json)，均通过。[B0 静态复验](../../personal-learning-suite/validation/b3c-b0-static-report.json)为 32 项通过、19 个来源指纹一致、本地链接无缺失。B0 检查仍区分历史 `created_in_b0=false` 与 B3c 实际资源，不把开发路径视为安装。SK06 的 UTF-8 `skill-creator` 结构校验通过。

独立前向试用使用 Skill、最小原始虚构请求和按需完整包，先冻结输出再与路线／D07 核对。请求包含可靠活动直接使用、同一支架补全的两卡组合与未知成本、允许查阅规格下的局部分支更新；候选、正式采用、实际教学和学习效果分别记录。[复核报告](../../personal-learning-suite/validation/b3c-review.md)未发现阻断三个情境返回的实现缺陷；实际程序覆盖仅两次 index、四次 load，保存与控制行为由软件测试另行覆盖。原始请求及[冻结回答](../../personal-learning-suite/validation/b3c-forward/answer-before-audit.md)保留读取程度和未执行范围。

这些结果不构成完整 B10 场景、真实课程试用、V1—V4 或因果效果验证。来源或包指纹不匹配时当前 manifest 的加载可能整体受限，这是保守发布门禁；影响追踪只覆盖已记录键／来源和对象引用，未知语义依赖仍未知。

## 可重新打开的虚构演示

[演示脚本](../../personal-learning-suite/scripts/demo_b3c.py)在新的 `B3c_虚构策略学习空间` 导入人工夹具，经 AG1 测试授权保存一份 S07＋X02 方法配置，然后新建适配器读回。现有空间只读；被删除、受限或不完整的空间不会被重新导入。

[首轮保存报告](../../personal-learning-suite/validation/b3c-demo-first-report.json)与[重复重开报告](../../personal-learning-suite/validation/b3c-demo-report.json)均为状态修订 2、31 个对象、复用状态 reusable、完整性 ok，新增表现和计划均为 0。演示夹具中既有的原答与安排是人工记录，不是本批发生的学习。示例请求见 [b3c-method-input.json](../../personal-learning-suite/fixtures/b3c-method-input.json)。

从项目根执行：

```powershell
python -X utf8 personal-learning-suite/scripts/build_b3c_resources.py --check
python -X utf8 personal-learning-suite/scripts/check_b3c.py
python -X utf8 personal-learning-suite/scripts/check_b0.py --report validation/b3c-b0-static-report.json
python -X utf8 personal-learning-suite/scripts/demo_b3c.py --workspace "examples/workspaces/B3c_虚构策略学习空间"
python -X utf8 personal-learning-suite/src/runtime/learning_strategies.py inspect --workspace "examples/workspaces/B3c_虚构策略学习空间" --request personal-learning-suite/fixtures/b3c-method-input.json
python -X utf8 personal-learning-suite/src/runtime/learning_strategies.py --help
```

`index/load` 不需要个人空间；`inspect/reuse/submit/change` 使用 `--workspace` 与 `--request`。普通 change 只读，明确 `--restrict` 才持久限制。CLI 请求、stdout、验证报告和宿主上下文属于组件外副本，SQLite 删除不覆盖它们；本批文件只含通用资源与明确虚构开发资料。

## 下一步

B3c 已提供 B4 Encoding／Post 专项需要的有限方法资源与配置接口。可按 B3a／B3b 各自交付状态进行后续教学、证据与计划集成；本批未自动串接这些工作流。以后有实际需要的卡再回原文核对和编译，不先做全库排名、复杂成本调度或自动研究更新。

真实课程、可靠参考、用户预算、个人保存范围、模型与宿主身份／写入／输出边界继续按首期输入清单落实。通用 Skill／资源的维护由独立开发流程核对发布，个人使用反馈不自动修改通用包。
