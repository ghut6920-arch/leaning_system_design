# F03 来源契约贯通修复

日期：2026-10-04。原审计目录与 `source-contract-result.json` 原封保留，不将旧失败改写成已通过。

当前结果：目标入口接受已有 B2b 三模态／`verification.content` 来源；原 B2a 单 Fact 输入保留读取兼容。同一明确范围的来源可经 B5 保存目标，再用于实际 MaterialUse 检查和提交。没有运行自动迁移、模态事实升级或专业内容正确性保证。

## 实现与接口

仅 `src/runtime/learning_goals.py` 需要运行代码修改，加入来源声明的统一表示与旧载体读取。B2b 和 B5 已能保存／检查统一表示，无需修改它们的运行逻辑。统一声明用 AG2 显式的 `verification.content.required_modalities` 指明当前核验范围；该字段缺失、必要模态 unknown、核验 pending／旧修订或锚点形状不合法时，关联要求保持 partial。非必需公式／图像未知仍保留。

共享契约、目标／材料接口与 B2a 验收说明补充相同规则；B0 的静态字段 JSON 不变，19 个设计来源和原 `fixtures/b2a-goal-input.json` 未改。`canonical_fixture()` 是测试显式构造的人工核验声明，不是运行转换器。

## 红绿证据

- `F03-source-contract-red.txt`：首个 public `goal.sources_submit → goal.submit → materials.submit` 用例失败；`F03-source-contract-green.txt`：最小兼容修复后通过。
- `F03-anchor-red.txt`／`F03-anchor-green.txt`：任意标签冒充管理锚点原先导致 complete；补形状检查后保持 partial。
- `F03-malformed-red.txt`／`F03-malformed-green.txt`：坏容器导致异常、布尔修订号冒充 1；修正后保守返回受限。
- `F03-read-scope-red.txt`／`F03-read-scope-green.txt`：单纯布尔“已读”不能替代可定位范围。
- `F03-material-use-green.txt` 与 `F03-final-canonical-b5.txt`：同一来源由 B5 保存目标；通过公开 LearningStore 保存材料准备 ActivitySpec 候选后，B5 `materials.inspect=compatible`、`materials.submit=committed`；精确来源未改写，材料锚点与用途 binding 保持，实际暴露 unknown。

## 最终专项回归

使用 `python -X utf8 -m unittest discover -s personal-learning-suite/tests -p <文件>`。原始输出分别保存于：

| 测试文件 | 结果 | 输出 |
|---|---|---|
| test_b2a_goals.py | 47 通过 | F03-b2a-regression.txt |
| test_b2b_materials.py | 31 通过 | F03-b2b-regression.txt |
| test_b5_entry.py | 41 通过 | F03-b5-regression.txt |

最终 helper 增加读清范围检查后又跑 B5 的两个 canonical 用例，均通过；全集和 B0 静态由根 agent 统一验证，避免并行改动期间生成错误全集结论。

## 保留边界

本切片仍是 FIX／synthetic 开发运行。测试声明不建立学科真伪、真实 AG2 身份或学习效果。材料准备候选未绑定教学／评分判据执行权，因此贯通检查只证明来源、材料与用途接口；不宣称教学 ready、展示已发生或目标已达成。原件锚点结构完整不证明它支持结论，专业相容性仍由责任方核对。旧来源进入材料阶段仍需显式补模态，未补齐时拒绝且数据库不变，这是合理停止。
