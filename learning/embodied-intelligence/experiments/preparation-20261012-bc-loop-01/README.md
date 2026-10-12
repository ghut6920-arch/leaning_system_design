# 本次备课过程归档

本目录为执行层事实归档，未作为教学Agent的额外输入。它保存实际可取得的输入、交接、返回、版本文件、规则快照和文件差异；不包含模型内部思考，也不作教学质量诊断或系统改造建议。

最终备课入口在正常学习目录：[first-stage-plan-v2.md](../../plan/bc-closed-loop-20261012/first-stage-plan-v2.md)。常规收口记录为 [preparation-result.md](../../sessions/2026-10-12-bc-preparation-01/preparation-result.md)。

- [原始完整任务](input/user-request.md)，其中包含完整学习者请求；[常规原始学习输入](../../sessions/2026-10-12-bc-preparation-01/raw/learning-request.txt)已保存读回。
- [实际过程索引](process-record.md)：每阶段输入、已读主要资料、输出、交接与修订定位。
- [全部版本对应](version-map.md)：旧版→当前版及实际变更原因；[逐版差异清单](diffs/index.json)由保留原件直接比较生成。
- [文件变化与仓库版本](file-changes.md)，[常规产物清单与SHA256](deliverables-manifest.json)，[归档文件清单与SHA256](archive-inventory.json)。后者不列其自身，以免自引用。
- [观测缺口](observation-boundaries.md)：不可获得信息及真实失败，不能把补存文件快照当原始工具转录。

`environment/` 保存入口、实际采用规则/策略资源字节快照、读取/快照清单、仓库HEAD、指纹与前后状态。规则依现有FRAMEWORK路径取得；Agent与Skill本次未改。`handoffs/` 是实际发送给Agent的逐字任务与续派，不补造未取得的直送载荷。`receipts/` 是实际返回；名称带verbatim的文本保留当时完整可见返回，少量较早定位整理版标为派生。`observations/` 保存可取得的根工具输入/输出和Agent消息；它不是完整平台会话导出。

`stages/01–11` 保留实际阶段产物及候选版本的字节快照；编号为归档位置，不代表并行阶段完全串行。`stages/07-reviewed-candidate` 是送审时保存的候选集合，实际被读活动版本以交接12和AG3原意见为准，不能将集合内所有旧版都算成已读。`stages/12-final-delivery` 只接最终采用的活动版本。所有可见旧版另留在正常学习目录及先前阶段快照，未覆盖。

已完成学科研究、认知设计、具体材料/题面/支持/参考、功能读回、正常AG3审查与有限采用。未实际授课、记录能力、运行实验或验证学习效果。原论文图像未取得可观看结果；AG3补取部分原文的网络失败和有限复核范围均如实保留。

复核时先读process-record与version-map，再按交接顺序查看当时版本、原始意见和对应差异。不要仅以最终成品倒推早期阶段已完成。首次环境快照在两份原始输入写入后取得；既有四个修改状态文件未被本次更改。外部套件提交号不可获得，实际规则用SHA256和119项框架指纹定位。
