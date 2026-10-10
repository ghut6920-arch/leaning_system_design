# 主审对新上下文首段的内容复核

日期：2026-10-05。复核对象是 teaching-forward-fresh 已实际生成并冻结的四份首回合，不是主审预写的理想答案。原请求来自公开虚构案例，没有学习者后续作答。生成者先读请求和当前 Skill，写出首段及指纹清单后才核原研究与设计；详细时序由其清单和覆盖说明提供。

主审此前已经看过第一位教学审查者的输出，故这里是跨执行者内容复核，不能称主审也处于无背景条件。三位本轮执行者都是同一系统下的模型子 Agent；没有跨模型、真人或全程技术隔离的独立性。

| 首段 | 实际内容和顺序 | 主审核查 | 尚未支持的结论 |
|---|---|---|---|
| [T1 卷积](reviewers/teaching-forward-fresh/T1-first-turn.md) | 先定义从零起的下标、域外为零和完整线性卷积，再以四条乘积贡献解释输出位置，得到 `[6,11,4]`；没有额外问题 | 四条贡献分别为6、8、3、4；中间位置两条相加为11。公式、位置表、结果相容。符合请求“完整示范、不测验”，不是只抛公式后让新手猜 | 没有用户原答，不能说其理解了卷积、能独立计算或跨情境使用 |
| [T2 分部积分](reviewers/teaching-forward-fresh/T2-first-turn.md) | 使用用户已给且正确的四项，直接给允许查阅的公式，接回同一原积分，留下最后一次积分和常数由用户写 | `∫u dv=uv−∫v du` 的代入一致；没有因忘入口就撤销已会内容，没有强制背公式或重学全章 | AI 已提供公式及代入，尚无最后原答；不能记作无帮助恢复公式或完整独立求解 |
| [T3 欧几里得算法](reviewers/teaching-forward-fresh/T3-first-turn.md) | 补公因子集合的双向不变，连接初始化、循环保持、非负整数严格下降和退出返回；再对应到用户待写的实现 | 由 `a=qb+r` 分别证明两组公因子相同；当前第二变量从B降到R，`0≤R<B`，直到B=0；退出gcd(A,0)=A。未混淆仅有下降与正确性。提醒使用旧值求余数符合实现接口 | 证明由AI提供，实现尚未生成；不能称用户独立证明或实现完成。有限枚举不能代一般证明 |
| [T4 系统误反馈](reviewers/teaching-forward-fresh/T4-first-turn.md) | 先说明R2中用户原答正确，改错误反馈，再列R1/R2的0及正数边界；保留R1合法使用，R2“不超时”写法未给则不补造 | 两版本对应题设准确，影响限于使用R2且传0的调用；没有将旧合法意义全撤销，也没有让用户为系统错误重考 | 题设没有实际评分或部署状态；只能确认本回合文本纠正，不能称实际记录、脚本或运行已经恢复 |

对应当前指导是 [内容准备](../../src/skills/learning-teaching/references/design-whole.md)、[Encoding](../../src/skills/learning-teaching/references/encoding.md)、[C0](../../src/skills/learning-teaching/references/c0.md)、[Post](../../src/skills/learning-teaching/references/post-encoding.md)和[方法选择](../../src/skills/learning-strategies/references/selection-adaptation.md)。四段分别执行必要输入、允许恢复入口、局部理由接整体、系统纠错，没有从问题数量、卡数或角色数推断教学质量。

本复核只支持这些首段具体路径的内容与请求相容。没有执行后续反馈、计划采用、课程保存或真实学习，不能由此宣布所有情境均通过或系统保证高效深度学习。

## 入口与连续性四例

下面四例由 entry-continuity-fresh 自行提出原始虚构请求，实际首段与审查索引分段保存。主审检查的是“当前入口生成的实际首段”，没有将索引中的未来约束算作实际执行。

| 首段 | 实际行为及主审核查 | 未完成或限制 |
|---|---|---|
| [E1 陌生模型纯讲解](reviewers/entry-continuity-fresh/01-unfamiliar-explanation.md) | 解释状态、控制和时间步，以3+2×(−1)=1完整演示；区分题设模型与现实测量，遵照不考、不入课程的请求收束 | 没有原答、现实实验或学习结论 |
| [E2 跨模型仅收束](reviewers/entry-continuity-fresh/02-resume-close-only.md) | 在λ>0下已给草稿的非负性和零值点确实支持存在；恢复文本逐字保留原草稿、此前提示与未知帮助，保留尚缺唯一性，未因只余五分钟降低完整目标 | 只生成待保存断点，无实际状态提交、宿主接管或后续排期 |
| [E3 原答评分异议](reviewers/entry-continuity-fresh/03-score-objection-original.md) | 零乘积两分支及±1代回正确；约去x−1需要x≠1，旧评语丢解。直接使用够用原答纠正评分依据，不重考或推广整章能力 | 原答是输入中的虚构原件；未知既往帮助仍未知，无正式Judgment提交 |
| [E4 看完整答案并换文字](reviewers/entry-continuity-fresh/04-transparency-format.md) | 按总量与人数求合并均值：(1×2+3×8)/4=6.5，与直接平均5作功能对照；展示完整参考后转为教学，不称自主选法通过，没有新题 | 未有学习者工作，不能说用户会合并均值；未写个人课程 |

这些首段落实了现有入口的用户控制、原件优先、帮助连续和预算收束。所有自然语言案例仅到已发生的首段，没有假设续答成功。

## 目标、材料与评价四例

下面四例由 design-assessment-fresh 新造自包含请求，主审读取了原要求、完整虚构原件和实际生成内容；原件不是任何真实用户的学习记录。

| 实际输出 | 主审具体内容核查 | 未完成或限制 |
|---|---|---|
| [R1 投影整体证明](reviewers/design-assessment-fresh/outputs/R1-projection-review.md) | 检查v=Pv+(v−Pv)、像核交集为零、直和定义的唯一分解→线性、幂等、像核以及反向映射唯一的连续推理；二维矩阵`[[1,-1],[0,0]]`确为指定非正交投影。没有把不对称误判为失败，没有只以矩阵算例代一般论证 | 支持本题在虚构给定允许资料及帮助条件下的完整作品，不支持任意线性代数能力或长期保持；无实际课程采用 |
| [R2 lower_bound修复](reviewers/design-assessment-fresh/outputs/R2-lower-bound-review-and-materials.md) | 原实现缺返回n的候选；空列表恰好返回0，不误报为空输入失败。教师参考的`[0,n]`候选边界、`[0,lo)`不合格／`[hi,n)`合格、合法访问及自然数区间严格缩短可支持一般正确性。280个小输入分别核原程序与教师参考，有限运行与一般证明分开；原作者自主选测试仍unknown | 主审核阅代码、一般参考与执行报告，不将审查者选的测试算为学习者工作。没有收到学习者修订；关键方法已提供，不能反记自主发现 |
| [R3 仿射源错误与图](reviewers/design-assessment-fresh/outputs/R3-affine-correction-and-materials.md) | 一点给3=2m+c，故全族y=m(x−2)+3；y=3和y=x+1均过(2,3)，y=1.5x也是成员但不唯一。主审实际打开PNG，核两线、交点、坐标轴与图例相容。图承担空间对应，代数承担全族完整性，显示窗口不改实数定义域 | 文字原答可直接重评；AI画图不补自主绘图证据。虚构错误参考的文字更正不是实际数据库或真实教学恢复 |
| [R4 简单计算即收束](reviewers/design-assessment-fresh/outputs/R4-simple-stop.md) | 给定公式允许使用，(3+7)/2=5已满足原数值目标。没有强加过程证明、图或延迟任务 | 只支持该次计算，不推广到其他目标 |

R2有限执行由该审查者实际运行，详细输入集合、失败例及范围在其执行JSON中；主审没有把重复运行同一脚本当成新的教学证据。[教师参考](reviewers/design-assessment-fresh/artifacts/R2-teacher-reference.md)和[执行结果](reviewers/design-assessment-fresh/artifacts/R2-execution.json)可回查。[R3持久保存的图件](reviewers/design-assessment-fresh/artifacts/R3-affine-comparison.png)也可单独查看；原始输出保留当时临时执行路径。

这四例显示目标、材料、完整作品和帮助解释能改变具体首段，支持本轮保留相关主干。没有比较不同教学配置的净收益，也没有将生成者后评算作独立评分。
