# 仓库版本与本次文件变化

学习目录开始与收口HEAD均为 `1bd3a8d93dbcfc17913787c7663a29b9d682a867`；没有提交、切换分支、推送或改Git配置。原始HEAD/状态在environment/git-head-before.txt、git-status-before.txt，结束状态在git-head-end.txt、git-status-end.txt。首次环境baseline在两份原始输入保存之后取得，不是零写入快照。

本次新增37份正常学习目录文件，其中21份为当前采用集合（包含原输入、最终收口、审查/检查原件及图两种格式），16份为保留的旧版。全部确切路径、SHA256、字节数及active标记见[deliverables-manifest.json](deliverables-manifest.json)。新增目录为：

- `sessions/2026-10-12-bc-preparation-01/`：原始学习输入与AG0有限采用记录。
- `materials/bc-closed-loop-20261012/`：专业、来源、实际材料用途各版。
- `goals/bc-closed-loop-20261012/`：目标v1。
- `artifacts/bc-closed-loop-20261012/`：认知设计及AG1功能检查各版。
- `plan/bc-closed-loop-20261012/`：初稿与最终备课入口。
- `questions/visible/bc-closed-loop-20261012/`、`questions/backup/bc-closed-loop-20261012/`、`questions/teacher-reference/bc-closed-loop-20261012/`：主线、图、备用及教师参考各版。
- `assessment/bc-closed-loop-20261012/`：先定问题、完整原审查及局部复核。
- `experiments/preparation-20261012-bc-loop-01/`：额外隔离的事实归档、快照、原交接/返回、差异及索引。

本次只在上述新目录增加文件，旧版未覆盖。18组相邻Markdown版本的实际差异在[diffs/index.json](diffs/index.json)；规则、环境及阶段快照是复制归档，未把复制行为当作新教学修订。首次候选和最终集合分别保留。

本次开始前已经处于修改状态的 `AGENTS.md`、`FRAMEWORK.md`、`MODEL_ENTRY.md`、`framework-manifest.json` 保持当时原字节。连同INTERACTION、state/control、state/current，共7份既有文件前后SHA256无变化，见[existing-files-end-comparison.json](environment/existing-files-end-comparison.json)。全119项正式框架指纹结束仍匹配，见[framework-fingerprint-end.json](environment/framework-fingerprint-end.json)。未改正式Agent/Skill、共享契约或系统架构，也未改旧学习状态。

外部 `personal-learning-suite` 的Git查询返回Permission denied，提交号不可获得。实际采用版本以environment/rules-snapshot、各read-and-snapshot清单和119项指纹定位，不猜套件提交号。

截至最终文件校验，116份阶段快照与对应正常原件SHA256一致，18组diff全部成功取得，正常新文件及本归档之外没有意外变更。结果在[final-verification.json](environment/final-verification.json)。Git差异工具曾提示未来可能进行行尾转换；本次未让Git写这些工作文件，快照/原件字节核对仍全部相同。

全归档内容清单见[archive-inventory.json](archive-inventory.json)，它列文件而不列自身；所有新增文件机器清单见[task-created-files.json](environment/task-created-files.json)，该清单也不列自身。未新增学习代码、可执行notebook、训练或实验结果。没有删除文件或形成真实学习者作品。
