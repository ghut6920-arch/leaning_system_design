# AI 个人学习系统：B2b 内容与材料 v0

日期：2026-10-03。承接[实施路线](../architecture/AI个人学习系统_Agent与Skill工作网络及实施路线_v0.md)第十二节 B2b、D03 工作包 4、D04 C0 第二／四节与 D10 领域差异；沿用已完成 B0／B1 的共用对象和保存入口。

状态：B2b 的有限开发切片已实现并通过虚构验收。交付 SK02 `learning-materials`、完整 AG2 开发态角色、精简材料与领域规则、文本段读取／用途检查／共享提交／纠错追踪辅助器。Skill 未安装，AG2 未绑定真实宿主，未执行真实课程教学或学习效果验证。

## 本批交付与实际边界

| 要求 | 实际交付 | 能证明什么 |
|---|---|---|
| SK02 四模式与六种结果 | [SKILL.md](../../personal-learning-suite/src/skills/learning-materials/SKILL.md) 与按需材料工作流、领域核验、运行资源 | 指导读取／准备／核验／纠错；先查原材料、可直接复用或暂不新增 |
| AG2 完整职责 | [AG2 角色](../../personal-learning-suite/src/agents/AG2-materials.md) | 内容与用途责任、输入、专业返回、采用、失败与控制边界；角色文件不实现身份／展示隔离 |
| 读取／正确性／用途／实际展示分开 | [MaterialsService](../../personal-learning-suite/src/runtime/learning_materials.py)、[局部接口](../../personal-learning-suite/contracts/materials-b2b.md) | 分模态 Fact、内容与用途核验声明、可见／备用／参考分区；实际展示保持未知 |
| 原件范围可定位 | `LearningStore.read_artifact_segment` | 同一受控 SQLite 快照读取指定合法行段，不顺带返回整份原件；文本提取不代表公式图像读清 |
| 复杂参考有核验路径 | [领域与对象规则](../../personal-learning-suite/src/skills/learning-materials/references/domain-checks.md) | 完整题面、域／量词、存在性、全部解、构造／下界、整体规格与开放论证所需依据；不足则保持未核，不把数值例提升为一般证明 |
| 同一保存入口 | 专业材料授权／采用、CAS、幂等、精确版本和控制门 | 材料正常用途提交后可重新打开；SourceFragment 也要求专业授权；不另建材料数据库 |
| 更正有两链与四责任 | `trace_change` 与 `change --restrict` | 已记录引用的内容／要求依赖导航；未知依赖保持未知；四恢复分别 pending，不自动改判、补测、改承诺或解除限制 |

共用语义保持 `pl-contracts/0.1.0`，保存承载保持 `pl-store/0.1.0`，材料适配为 `pl-materials/0.1.0`。嵌套规则单列在局部接口，公共对象字段继续只维护于原共享契约。既有设计／研究原文和 B0 的全情境 `not_executed` 保留。

检查器的 `compatible` 表示声明结构、引用、当前用途和已标注操作满足本切片；**不证明学科结论正确**，不自动发现未标注的语义／视觉泄露，也不证明真实专业核验或展示已发生。实际 AG2 仍需依据来源、完整推导、规格测试或适当专业审查完成核验，不能用模型一致或策略研究支持替代。

## 实际验证

[B2b 行为报告](../../personal-learning-suite/validation/b2b-runtime-report.json)记录 **30 项通过，0 失败、0 错误、0 跳过**。所有空间为隔离临时目录，资料、目标、原答、预算、授权和接责都由人工虚构夹具给出。覆盖合法行段、越界／定位拒绝、分模态与必需缺口、双轴核验、锚点、四领域声明、用途变化、标题／版式潜在代做、展示未知、保存重开、专业授权、旧状态／旧依据、幂等、暂停／限制、删除迟到和双链四恢复。另用真实 CLI 子进程验证限制门先提交、追踪后返回。

[B1 回归报告](../../personal-learning-suite/validation/b2b-b1-regression-report.json)为 33 项通过；[B0 静态复验](../../personal-learning-suite/validation/b2b-b0-static-report.json)为 32 项通过、19 个来源指纹一致、本地链接无缺失。静态检查只放行目前实际开发的 SK00／SK01／SK02，仍不允许把目录数视为安装状态。`skill-creator` 的 UTF-8 结构校验通过。

复核修正了两个实际问题：嵌套 `requirements/*/content_basis_refs` 的内容依据不再被归入要求链，边保留字段定位；检查旧来源修订时也直接返回受限，正式提交仍保留共享入口的最终版本门。

专业行为前向试用及检查边界记录于[独立复核](../../personal-learning-suite/validation/b2b-review.md)。其原始请求明确为人工虚构：漏零解参考与既有完整原答，以及一般性高级目标只提供数值验证。候选材料／交接与正式专业采用、历史重评、实际教学恢复分别报告，不能把本次模拟当真实学习。

## 可重新打开的虚构演示

项目根下 [B2b 虚构材料空间](../../examples/workspaces/B2b_虚构材料学习空间/records.sqlite3) 使用独立数据库，未改 B1 演示空间。人工夹具导入后，通过 AG2 测试配置提交一份正常用途材料，再新建适配器读取。当前状态修订 2、29 个对象、2 份人工原件，用途检查 compatible，完整性 ok；没有新增表现、评分或计划。

[演示脚本](../../personal-learning-suite/scripts/demo_b2b.py)首次创建空间，已有空间只读。重复运行仍为同一修订和对象数；已删除或受限材料不会被重新填入。重开／重复执行结果见[演示报告](../../personal-learning-suite/validation/b2b-demo-report.json)，首轮持久保存由行为用例另行验证。

从项目根运行：

```powershell
python -X utf8 personal-learning-suite/scripts/check_b2b.py
python -X utf8 personal-learning-suite/scripts/check_b1.py --report validation/b2b-b1-regression-report.json --output validation/b2b-b1-regression-output.txt
python -X utf8 personal-learning-suite/scripts/check_b0.py --report validation/b2b-b0-static-report.json
python -X utf8 personal-learning-suite/scripts/demo_b2b.py --workspace "examples/workspaces/B2b_虚构材料学习空间"
python -X utf8 personal-learning-suite/src/runtime/learning_materials.py --help
```

材料 CLI 的 `read/inspect/submit/change` 使用 `--workspace`、`--request` 指定虚构目录和 UTF-8 JSON 请求。payload 见材料局部接口；默认更正追踪只读，显式 `change --restrict` 才建立共享用途门。输出和请求文件是调用者副本，不在组件删除范围。

## 下一步边界

本批完成有限 SK02／AG2 开发，不安装七包、不部署四角色或扩展课程目标。现有 B2a 开发资源继续保留；目标和材料仍需在真实实例的近期用途下互核，然后才能进入 B3a 评估与 B3b C0 教学。可靠且有限的虚构目标和参考已可供这些批次开发，不要求建全课程材料库。

真实课程、PDF/OCR／公式图像工具、真实来源及核验能力、个人保存范围、模型、预算与宿主身份／写入／输出边界仍待实例化。普通候选 partial／pending／error 保持受限；本助手不将其保存成正常用途材料。专业限制暂没有恢复 API，纠正后仍由相应责任方提供恢复依据。V1—V4、B10 全情境、真实课程试用和学习效果仍未验证。
