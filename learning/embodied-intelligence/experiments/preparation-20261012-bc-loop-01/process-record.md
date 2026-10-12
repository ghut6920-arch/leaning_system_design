# 实际工作过程索引

本文件于备课收口时，从已有输入/返回、实际文件、阶段快照和交接整理。它是定位索引，不替代逐字原件；精确逐项时间、子Agent完整底层工具转录与内部草稿不可获得。实际主要顺序为下表，规则预读及AG3用途问题与AG2研究有并行重叠。

## 0. 环境与原始输入

完整用户任务：[input/user-request.md](input/user-request.md)。嵌入学习请求原件：[sessions/raw/learning-request.txt](../../sessions/2026-10-12-bc-preparation-01/raw/learning-request.txt)，根入口保存后读回。背景是学习者自报，没有本次测评。

根入口实际取得AGENTS、state/control revision11、state/current revision22、MODEL_ENTRY、FRAMEWORK、INTERACTION；按FRAMEWORK取共享契约、AG0/SK00/session-entry与当前SK03必要正文。入口和规则快照在environment/entry-snapshot与rules-snapshot；逐项路径/哈希见各read-and-snapshot.json。最早两次读取完整响应未持久保存，文件快照可取得，响应缺口已记，不伪造。

学习目录HEAD为`1bd3a8d93dbcfc17913787c7663a29b9d682a867`。既有AGENTS/FRAMEWORK/MODEL_ENTRY/framework-manifest已经处于修改状态。外部personal-learning-suite Git查询Permission denied，其提交号不可获得。采用本次实际规则快照及SHA256；119项框架指纹开始/结束均匹配。Agent当前指导2026-10-11；共享契约pl-contracts/0.1.0，策略资源pl-strategies/0.1.0，Encoding R07来源library_version 2.0。具体文件版本以原件为准，不把日期当提交号。

只有现有AG0父入口、AG1设计/计划、AG2专业/材料、AG3审查；分工使用同一工作目录的真实子Agent，未新增教学角色。初始三次派发完整输入在[initial-dispatches.json](handoffs/initial-dispatches.json)。各Agent有明确目录ownership，不回滚他人编辑。实验归档未交给教学Agent；旧专题审计报告未读也未用于判断，规则内历史链接没有沿入。

## 1. AG2学科研究

开始输入：交接order1、原始学习请求、现有AG2/SK02及SK03学科转教学路径；尚无本次认知稿。AG2真实读取清单见[来源回执v1](stages/02-ag2-research/materials/bc-closed-loop-20261012/source-notes-v1.md)、environment/ag2-rules-read-and-snapshot.json及[研究返回](receipts/ag2-research-return-verbatim.md)。

外部主要资料是DAgger PMLR固定2011稿、robomimic PMLR稿、ACT arXiv v1、Diffusion Policy arXiv v3。实际段落/公式/版本/失败与未核模态逐来源保留；没有复制原论文图表或声称完整复现。专业成果包括闭环对象链、同误差不同反馈对照、非法均值与延迟对照、竞争机制、实验与条件化改进范围。

完整产物为disciplinary-research-v1和source-notes-v1，保存在stages/02及正常materials原件。根入口正式[order5→AG1](handoffs/05-ag2-to-ag1.json)，AG1随后确认全文收到两份v1（messages-01 sequence6）；此前AG1只加载规则，未先定认知任务。没有阻断回问。

## 2. AG3从原用途先形成问题

开始输入：交接order2、原始请求、AG3/SK04/product-review、共享契约与学科转教学规则。AG3先直接读Ross原文与robomimic作者页，从用途提出Q1–Q9，尚未读本次作者专业/认知稿；这些问题没有变成额外学习者作业。

完整输出[review-questions-v1.md](stages/01-ag3-purpose-questions/assessment/bc-closed-loop-20261012/review-questions-v1.md)，原始返回[用途问题回执](receipts/ag3-purpose-questions-return-verbatim.md)，规则路径及快照在environment/ag3-rules-read-and-snapshot.json。完成此步后等待实际候选成品，没有在此时验收尚不存在的材料。

## 3. AG1认知分析、整体设计及计划v1

规则预读输入：order3及原请求。真实规则加载返回[ag1-rule-loading.md](receipts/ag1-rule-loading.md)。正式设计输入为order5的AG2两份v1；AG1实际取得AG1、SK01、SK03/design-whole/Encoding/Post、SK05及SK06所需正文，以及完整Encoding R07、Post retrieve-relation/select-method和共同约束。资源读取/哈希见environment/ag1-rules-read-and-snapshot.json、strategies-read-and-snapshot.json及认知稿读取回执。

完整输出：goal-v1、cognitive-design-v1、first-stage-plan-v1，字节快照stages/03，完整[设计返回](receipts/ag1-design-return-verbatim.md)。R1–R4由一份连续“闭环失败分析与实验判断说明”承担，M1–M5明确教师材料与学习者工作、备用支持及多解参考功能。v1计划真实状态是design_prepared_materialization_pending，未倒改为已完成。

向AG2交付三份实际v1和具体材料需求：AG1直接通知的逐字载荷父入口不可获得，见[边界说明](handoffs/direct-notification-boundary.md)；根入口正式[order8制作续派](handoffs/08-ag1-to-ag2-materials.json)逐字保存。AG2确认三份全文接收（messages-02 sequence10）。没有需要补专业研究才能继续的回问。

## 4. AG2材料落实与首次AG1功能读回

制作输入为上述Goal/认知/计划v1。AG2在等待期间按[order7](handoffs/07-material-rule-preload.json)补读design-whole、materials-examples、INTERACTION，真实读取回执[material-rules](receipts/ag2-material-rules-return-verbatim.md)。这些是正常材料落实所需规则，未读取审查问题或实验归档。

AG2实际生成四份visible-v1和闭环SVG-v1。根入口保存stages/04后正式[order9](handoffs/09-materials-to-ag1-functional-read.json)交AG1读回；当时备用/教师参考/用途仍在制作。AG1读取四份正文，最初PNG缺失，随后AG2渲染PNG，AG1实际view_image查看并保存materialization-check-v1。PNG与SVG原件均保留，未将渲染前状态写成当时已具备。

AG1完整[首次功能返回](receipts/ag1-functional-check-return-verbatim.md)及stages/05检查原件。实际局部意见是明确标准和横移扰动两条件的初始速度同样为0，避免同时变化的歧义；未改目标或新增任务。根入口[order10](handoffs/10-functional-feedback-to-ag2.json)实际转交该反馈，未请求逐题扩充。

## 5. AG2局部修订与完整材料交付

AG2保留主案例v1，另存04-v2澄清两条件速度都0，导航及支持/参考另存新版本。根入口[order11](handoffs/11-navigation-version-check-to-ag2.json)要求核当前定位、保留旧版。AG2核来源时自行发现Diffusion Policy三时域章节号误记，保留专业/来源v1，另存v2改§III-C为§II-C并补记实际读取范围；内容机制与认知目标不变。这是实际发生的定位修订，不是AG3造成的专业返工。

完整可观察修订及图在stages/06、08和正常questions/materials各版本；逐版差异在diffs。最终主线01-v3→02-v3→03-v2→04-v2、图v1、support/reference-v3、专业/来源-v2、material-uses-v3，完整[AG2材料返回](receipts/ag2-material-return-verbatim.md)。用途v1→v2→v3澄清责任方、历史时点和位置输入缺速度信息概述。

根入口向AG3送审时，确切活动版本由[order12](handoffs/12-ag3-review-candidate.json)指定：最终可见主线/图/支持/参考、goal-v1、专业/来源-v2，但作者用途总结是当时material-uses-v1。stages/07保留该时点候选集合，未以后出的用途v3替换送审快照。AG2完整返回与最终用途版本另在stages/08。

## 6. AG1最终功能读回

输入为[order13](handoffs/13-ag1-final-functional-read.json)当前主线/主案例/备用/参考/专业v2；其后[order14–15](handoffs/14-15-final-use-version-notices.json)告知最终MaterialUse-v3。AG1读当前04-v2、support/reference-v3和来源修订，实际比较稳定正文导航/章节变化，另存materialization-check-v2。收到用途v3后又另存v3补充，未覆盖已观察v2。

完整输出stages/09三版检查及[最终功能返回](receipts/ag1-final-functional-return-verbatim.md)。v2/v3共同承接当前功能确认，无新的认知缺口；此时AG3/AG0采用仍pending，不倒写计划v1。

## 7. AG3正式反向审查和局部复核

实际输入为order12送审清单及之前原用途/先定Q1–Q9。实际顺序与已读版本在[原始完整review-v1](stages/10-ag3-review/assessment/bc-closed-loop-20261012/review-v1.md)：先四份可见输入/题面及实际图，再多解参考与支持，之后目标/专业/来源，最后作者认知/计划/用途总结。AG3对可推导模型和有限材料实质核验，没有将作者总结当作成品替代。

AG3原意见充分并建议采用，无新目标/任务/媒体要求；F1是当时MaterialUse-v1概述中“缺位置输入”用词不准确。可见正文/参考已正确，最终MaterialUse-v3在该原意见保存前已存在，不能将其订正归因于AG3或编造一轮被迫返工。

收到最终用途版本通知后，AG3实际局部读MaterialUse-v3并保存[review-v2](stages/10-ag3-review/assessment/bc-closed-loop-20261012/review-v2.md)，核用词与当前版本相容，维持充分结论，无未解决阻断。完整[审查返回](receipts/ag3-review-return-verbatim.md)。未重复全文稳定材料；v2不是隐藏原意见后的“第一次通过”。

AG3尝试补取ACT/Diffusion/robomimic PDF的两次web与connector备用请求发生网络连接失败，没有取得新正文；实际直接原文复核范围与未取范围写入两份审查，不当成作者资料缺失或完整独立来源复核。未做学习者能力判断。

## 8. AG0有限采用与AG1计划收口

根入口全文读回review-v1/v2和AG1功能稿，实际采用当前纸面第一阶段有限准备；[order16收口输入](handoffs/16-final-preparation-adoption-to-ag1.json)逐字保留。AG1实际全文读两份审查，另存first-stage-plan-v2，保留v1pending快照，接最终版本入口。

完整计划收口返回[ag1-plan-closeout-return-verbatim.md](receipts/ag1-plan-closeout-return-verbatim.md)，stages/11保存两版计划。根入口随后全文读回v2，正常sessions/preparation-result记本次有限采用。stages/12保存最终活动交付。AG0为唯一用户教学入口，本次没有开始授课。

## 9. 执行层归档收束

执行层从真实原件生成版本对应表、相邻版本diff、当前产物manifest、全归档inventory、Git状态/新文件清单和既有文件前后哈希检查，没有把这些索引交给教学Agent。未发生的交接/回问/草稿没有补写。

已完成本次授权的纸面备课和可获得过程归档。未执行教学、学习者回答/作品、实际反馈/能力判断、训练/仿真/机器人实验、真实根因确认或效果验证；预算/活跃时间未知。不是流程卡在依赖，有限备课已收束。不可获得的提交号/工具转录/图像及网络失败以原始限制保留，见[observation-boundaries.md](observation-boundaries.md)。所有新增/修改文件和版本关系分别在file-changes及version-map；本文件不提出教学诊断或系统改造建议。
