# 协调器日常入口

AG0负责专业规划和最终采用，AG1/AG2负责各自产物，AG3负责明确版本的审查。日常只读本页和当前专业规则；内部事务、恢复和字段协议按需查[完整协议](coordinator-protocol.md)。

新单元/实质回修备课默认由[正常备课启动入口](preparation-runtime-start.md)自动登记当前聊天、初始化一次项目运行表并启动或复用Python伴随进程，实际分发AG2、AG1、AG3。AG0取得持久计划与真实监听接管回执后结束当前轮，由Python等待和唤醒原聊天；接管失败明确处理，不退回模型轮询。普通反馈可单入口完成；用户明确改变方式或实际能力限制时说明具体缺项。登记业务任务与启动真实执行者是两个动作，do assign并不会自动启动模型。

从项目根调用[日常程序](../scripts/coordinate_agents.py)，工作区需已初始化：

```powershell
python -B -X utf8 personal-learning-suite/scripts/coordinate_agents.py --workspace learning/embodied-intelligence --role AG0 desk
```

`desk`只返回本角色必要的任务、实际回执、依赖变化和待决定事项，可加`--task 任务ID`或`--use teaching --scope M2.1`，`--limit 12`。筛选只改变显示，不授予其他角色权限。工作状态为`running`、`submitted`、`blocked`；未开始的任务显示待开始动作，不伪装正在运行。没有百分比，文件存在也不能代替提交回执。

| 当前工作 | 日常操作 |
|---|---|
| 了解任务或异常 | `desk`；`alerts --consumer 当前上下文稳定ID`取得新版本/异常提示 |
| 登记、开始、提交、给意见或采用 | 将明确意图写为JSON，`do --intent-file 意图.json` |
| 同角色多个已明确动作，中间无专业工作 | `batch --plan-file 批次.json`；遇错停止，返回短状态和原回执位置 |
| 需要先核对一个具体决定 | `prepare --intent-file 意图.json`，核对返回的决定，再`apply --ticket 原ticket` |
| 查当前采用版 | `current --artifact-id 产物ID --intended-use teaching --scope 范围`，默认经原门禁核验后只返回元数据 |
| 查看固定输入及读正文 | AG0的`inputs --task 任务ID`默认只回已核输入目录；AG1/AG2/AG3默认正文。AG0承担专业职责时显式`--view text`；可用`--input 0`选原件。正文总窗口8000字符，按coverage续读 |
| 提交结果未收到或需恢复 | `saved --ticket 原ticket`，整体响应丢失则`saved --intent-file 原意图.json`；历史回执不等于当前可用 |
| 只在必要时查看完整依据 | `inspect --task 任务ID`，或下述技术入口的diff/receipt |

`do`在一次调用中准备并提交意图，返回可恢复的ticket；同路径文件且相同意图的重复do沿用原请求，不按当前状态重新编译。整体响应丢失可用原意图文件查saved；确实重新考虑后用prepare创建新决定或另存新意图文件。`prepare/apply`是可选的决定核对方式，不增加用户确认流程。状态、文件或控制变化可拒绝旧决定，不自动刷新指针或改变专业意见；历史提交仍按当前控制查询，查到回执不等于当前可用。

## 必要专业决定

登记时明确任务、产物ID/类型、范围、用途、所需输入和是否要求AG3审查。程序填写状态号、操作ID、指纹和采用指针，不判断学科依赖、审查政策或专业结论。

下列每行是一个独立意图文件的示例；范围和用途按真实任务填写：

```json
{"action":"assign","task":"M3-material","output":{"id":"M3-material","type":"MaterialUse"},"scope":["M3"],"use":"teaching","inputs":[{"artifact":"cognitive-design","scope":["M3"],"use":"teaching"}],"review_required":true}
{"action":"begin","task":"M3-material"}
{"action":"deliver","task":"M3-material","path":"artifacts/M3-material-v2.md","changed_scope":["M3"]}
{"action":"opinion","task":"M3-material","outcome":"supported","rationale":"说明实际核对的内容和适用条件。"}
{"action":"assign_review","task":"M3-review","from_task":"M3-material"}
{"action":"opinion","task":"M3-review","outcome":"supported","rationale":"说明目标版本、实际审查内容及边界。"}
{"action":"adopt","tasks":["M3-material"]}
```

AG0登记及采用；产物负责人开始、交付、专业确认；AG3的审查任务也先`begin`再读取`inputs`和提交`opinion`。`outcome`由专业方填写`supported`、`partial`或`rejected`，不能为通过门禁而虚构。采用意图明确选择已交付的任务，程序绑定该任务确切结果和适用回执，旧审查不会自动覆盖新版本。一次采用多个相互依赖的成果，可在`tasks`中明确列出。

默认输入取指定用途/范围的已采用版，并在开始时固定；同一任务始终读自己的`inputs`。新候选不替换已采用版。只有真正依赖待完成结果时，在输入项明确`after_task`并在登记意图给`wait_ms`；指定非采用版时明确`revision`及`provisional_conditions`。修订默认以覆盖本用途/范围的唯一已采用版为基版，存在多个基版时明确`base`或拆分任务。下游变化提示由专业方决定局部补核或修订，不扩大为全局等待。

作者确认的依据问题若**仅为input_not_adopted**，实际专业核验充分时可在opinion显式写`"allow_provisional":true`；字符串不接受，也不自动添加。`provisional_conditions`声明候选输入条件，`allow_provisional`声明作者接受这次暂定确认，二者不同；其他变化仍须复核/修订。暂定确认不代替上游采用或AG3审查，AG3沿自己的审查门禁。

AG1需要对已提交候选做功能读回时，AG0用如下意图，再由AG1 `begin`及`inputs`取得自己的固定快照。它复用普通ActivitySpec生产任务，报告仍是AG1成果；不用先启动AG3或复制正文。scope/use必须属于源成果，候选条件和审查政策均显式填写：

```json
{"action":"assign_readback","task":"M3-functional-readback","from_task":"M3-material","output":{"id":"M3-functional-report","type":"ActivitySpec","validation":"utf8"},"scope":["M3"],"use":"teaching","review_required":false,"provisional_conditions":"仅对这个固定候选做功能读回；不宣称正式采用。"}
```

控制投影陈旧时，AG0先`control-status`取得现投影sha和变化的原件/实际sha，按原件显式解释全部`paused_ids/deleted_ids/restrictions`。另存完整JSON投影，保留同一组source_refs，填写递增state_revision、新来源sha和`interpretation_rationale`；用`control-update --projection-file 原解释.json --expect-projection-sha256 现投影sha`原子替换。程序拒绝缺字段、陈旧源、换源及覆盖他人更新，不推断Markdown语义，不自动刷新指纹放行。该操作不更新学习control或数据库指针。

收到alerts后，用`{"action":"ack","consumer":"当前上下文稳定ID","through":返回的through}`确认；读取不会自动确认，也不会自动注入正在推理的模型。关键节点仍重新校验。控制变化、失败或超时按提示处理；需终止时明确`stop`的`task`、`outcome`（`failed`或`cancelled`）和`reason`。

局部继承审查、冲突意见处置、`check_change`复核，以及初始化、原子安装文件、历史导入、恢复检查使用[完整协议](coordinator-protocol.md)及[技术入口](../scripts/coordinate_preparation.py)。正常工作不必遍历这些内部字段。协调任务完成不等于学习发生；用户控制、学习事实和安排仍由原control/current/plan维护，角色仍为可信本地操作员声明，同模型兼任不称独立复核。

## 完整读取与阶段执行

正文返回`sha256`、`coverage.start/end/total`、`has_more/next_offset`及视图指纹。`complete`只表示本次输出覆盖全文，不证明模型实际已读；多段覆盖需按同一版本实际取得全区间。输入续读用`inputs --task 任务ID --view text --input 0 --offset next_offset --expect-sha256 原sha256`，编号从0起；查采用正文用`current ... --view text`，续读同样绑定字节指纹，指针变化不静默拼接旧版。明确需要全文时在文本视图加`--full`，仍受下述总返回预算约束，超出时按实际coverage续读；改变窗口用`--max-chars`。非文本按路径查看仍核其指纹。程序始终使用门禁已核的确切字节，不先回路径再读可变最新版。

技术入口的`current`同样默认元数据；机器客户确需旧编码正文时显式加`--view base64`。`snapshot`是技术字节接口，维持原编码契约，普通模型读取用日常inputs。

策略日常读取和普通长文用[资源阅读程序](../scripts/read_learning_resource.py)，例如`python -B -X utf8 personal-learning-suite/scripts/read_learning_resource.py --file personal-learning-suite/resources/strategies/post/retrieve-relation.json --view strategy-runtime`。这是源绑定的完整运行契约，必要字段、完整规范卡、共用约束、操作/研究混合段及研究边界均保留；相同完整原值共享一次。具体义务和研究展开触发沿[选法规则](../src/skills/learning-strategies/references/selection-adaptation.md)。需要原研究条目用`--view strategy-research --section /evidence_refs/0`，Encoding通常用`/research_excerpts/0`，须明确一份档案及指针；全档案仍用`--view strategy`。普通长文用`--view text`。

默认直接呈现正文及覆盖元数据，机器读取可选`--format json`。已选多包可重复`--file`，共享值类型和用途保留；按`--offset`续读并带前次`--expect-view-sha256`，任一契约/档案变化即拒绝。源指纹或输出覆盖不证明专业阅读/论文核验；不用先全档案再重复提取。批次资源项可指定`view:strategy-runtime`或`view:strategy-research`与`sections`列表，其余总预算和接收检查沿下文。

manifest用同一程序`--file learning/embodied-intelligence/framework-manifest.json --view manifest`，默认仅显示异常及全清单校验计数；需要角色条目时重复`--entry 清单中的确切路径`。筛选不缩小核验覆盖，指纹不能证明专业内容正确。超大网页和其他工具结果也先限定当前命题范围或保存完整结果并取必要片段；仅确有必要时展开全文。

日常只读视图和资源程序默认**总返回8192 UTF-8字节**，计入封装、正文和结束标记；`--max-return-bytes`可显式调整，字符/token不是等值预算。目录元数据本身超出时拒绝并要求缩小条目，正文超出时返回精确前缀及续读点；不静默丢字段或把缺口当读完。资源正文尾部为`READ_END`加校验，JSON返回末尾有delivery标记。

必须全文阅读的专业包可校准较大总窗口，避免保守小窗口增加往返。本次冻结M2.2四包用24576字节预算，六页无重叠取全；首批实际工具计数6144 token，在内层8000、外层10000预算下完整。这个校准只适用于该返回形态；更换内容/封装仍核尾标记，不把字节数机械换成token。

多份状态文件、策略或固定输入同批读取，用[批次程序](../scripts/read_learning_batch.py) `--request-file 批次.json --max-return-bytes 8192`，禁止把多个大页面直接合并输出。JSON的`version`为`read-batch/0.1.0`，`jobs`最多8项且id唯一；相对路径从批次文件目录解析。资源项为`{"id":"control","kind":"resource","files":["实际原件路径"],"view":"text"}`；协调项为`{"id":"material","kind":"coordinator","workspace":"实际工作区","role":"AG1","command":"inputs","task":"M3-functional-readback","input":0,"view":"text"}`。续读在原项填写`offset`和资源`expect_view_sha256`/协调`expect_sha256`，批次保留各项缺口，共享最终预算。程序只允许读命令，不接受do/apply或任意shell。

网页先用来源工具取得命题所需范围；需要长原文时先保存完整文本及来源定位，再由资源/批次程序读取该快照。这里不拦截宿主直接网页返回，也不能撤回已经进上下文的全文。普通入口/状态文件也走该有界路径，当前控制的必要字段须实际取得，不能只看指纹。

接收方先确认最终展示完整尾标记。需要程序复核时，把**实际收到的原始文本**交[接收检查](../scripts/check_read_delivery.py) `--file 捕获.txt`；不得以发送端副本或重构文本证明宿主已展示完整。缺标记/校验不符则不认可该页，缩小窗口后重取；已确认的区间保留。校验只确认捕获层边界和内容，不证明模型已读、来源真实性或另一层展示完整。外层工具预算仍须足够容纳这一份有界返回，不再合并第二份长输出。

启动、等待、交接、审查时机及有限恢复按[有界备课执行](preparation-execution.md)；AG0组织专业依赖，阶段结束后停止无增量探索，不创建常驻调度Agent。

主入口按该页“当前决定→必要输入”表读取。只查询状态/版本时复用元数据；亲自承担专业决定时读取实际正文。阶段交接沿现有checkpoint的备课部分，保存结果、验证范围、缺项、下一责任和固定原件定位；接任核当前控制、状态与必要原件，不复制探索历史或仅凭前任已读声明宣布完成。

## 控制批次

混有历史的状态/入口Markdown可先用`read_learning_resource.py --file 实际原件 --view outline --format json`取前12个ATX标题；heading-start/heading-limit续目录。目录不解释哪条状态有效、也不算正文已读；明确所需标题后，用原text视图的offset=start、max-chars=end-start、expect-view-sha256=source.view_sha256取得完整原段，超预算按实际coverage补到该段end，不自动读至全历史末尾。preface_end标出文首未归标题的范围，存在且影响决定时也读；标题不清/未闭合代码围栏/状态关系不明时回足够正文。控制有效性及实际原答/帮助仍照原规则核对，不由标题号推断。读取批次resource项支持heading_start/heading_limit。

`coordinate_agents.py --workspace 工作区 --role AG2 batch --plan-file 批次.json`。JSON只含`version: control-batch/0.1.0`及1–16项steps；每项只有唯一短id和完整intent，整批沿同一角色执行。必要字段先整批检查，实际权限/状态逐步核。实际专业核验完成、文件保存、意见明确后，可合并：

```json
{"version":"control-batch/0.1.0","steps":[
  {"id":"deliver","intent":{"action":"deliver","task":"M3-material","path":"artifacts/M3/sources-v1.json"}},
  {"id":"confirm","intent":{"action":"opinion","task":"M3-material","outcome":"supported","rationale":"实际核验的具体发现/边界，引用原报告。"}}
]}
```

例子不授予supported。begin与专业工作之间不批处理，采用仍需必要意见/审查。默认8192 UTF-8字节返回预算，批次至少2048；完整程序回执在receipts_path的逐条JSONL，权威仍是原ticket/数据库回执。遇错后续不开始，已提交不回滚。

重复同路径原批次先查saved，已committed不重复执行；拒绝不重编决定，确需重试原ticket才用`--retry-stopped`。未知提交先查saved并确认旧执行已结束，仍未知则停。内容改变须核当前状态、另存新批次；原路径改内容会拒绝。损坏/截断日志保留原件，按`requests/intent-*.json`查原ticket的saved，不能删日志重跑；意图索引source为`batch:批次绝对路径:步骤id`。control_batch_busy须先核原执行/回执，遗留锁不自动抢占。不把整份日志送回主入口。

## 材料清单与成员读取

有正式整体任务的新单元/实质回修给AG2的MaterialUse输出使用`validation: preparation_sources`，其余scope/use/inputs/review_required照旧；纯讲解沿原合格内容载体，不造题。begin后专业方实际准备原件，成员JSON数组每项只有id/kind/path；至少唯一formal_task、mainline、完整teacher_reference、唯一material_report，可按需要加backup_help/visual/code/verification。一个整体作品的题面各段在同一原件，独立单元可各有其包；代码仍在code/。

```json
[
  {"id":"task","kind":"formal_task","path":"questions/visible/M3-task-v1.md"},
  {"id":"lesson","kind":"mainline","path":"questions/visible/M3-mainline-v1.md"},
  {"id":"reference","kind":"teacher_reference","path":"questions/teacher-reference/M3-reference-v1.md"},
  {"id":"check","kind":"material_report","path":"artifacts/M3/material-check-v1.md"}
]
```

`build_preparation_sources.py --workspace 工作区 --task M3-material --members-file 成员.json --output artifacts/M3/sources-v1.json`仅为运行中的AG2清单任务生成当前draft_ref的静态清单，核控制/固定输入及成员字节，独占新路径、拒绝覆盖；不提交/确认/采用，不证明专业正确。随后deliver此JSON，opinion引用实质报告，再沿原AG3/AG0门禁。字节表仅在清单，报告引用路径/版本和成员id、保留实质发现，不抄题面/参考或SHA表，不嵌入清单SHA造成循环。

提交、意见和取用会核全部成员字节；变化须新版本与补核意见，不能刷新旧SHA沿用结论。重复路径/字节、第二份正式题面、缺教师参考指针、错误身份/用途/范围及控制/实时状态路径均拒绝；语义重复和参考质量仍需实质核验。历史utf8包照旧，不覆盖旧教材。

清单成员是包内未单独登记的静态原件；已单独登记的依据有自己的身份/用途门禁，须作为固定任务输入引用，不能通过清单原路径绕过。

功能读回沿assign_readback取得本角色固定输入，`inputs --task 功能读回任务 --input 0 --source reference --view text`取确切成员；采用版用`current --artifact-id 材料id --intended-use teaching --scope 单元 --source task --view text`。source只接受清单成员id，不是任意路径；角色/控制/未begin/版本门禁保持。各页按原预算、coverage及expect-sha256续读，读取批次的coordinator项可加source，共用总预算。非文本先metadata取路径/sha再实际查看。

清单编号从实际`inputs --view metadata`目录定位，0只是上例单输入的编号；审查任务可能先列上游再列目标。AG3可先核目录，作者正文仍在按原用途/必要原始依据定问题之后取得。

AG0接阶段发现、边界、异常和清单/回执定位，亲自判断时展开必要正文。阶段checkpoint合并，不每条控制响应另造报告。AG3保持原用途/必要原始依据→作者设计、实际成员/完整参考→作者总结；清单和回执不证明已读或正确。
