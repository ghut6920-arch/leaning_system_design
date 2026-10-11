# 备课范围与接入依据 / revision 1

日期：2026-10-11，Asia/Shanghai。单元键：PREP-TRANSFORMER-KV-20261011-R1。身份：AI 生成备课成品，供用户审查；不是正式课程目标、已发生教学或学习者表现。

## 当前请求原文

> Transformer Attention 机制中的 KV Cache 与长上下文推理，我要对这个单元进行测试备课，检验学习系统，现在你需要开始备课，依据当前启动提示词，学习系统框架、研究与设计方案，交付完整认知主线、实际材料与连贯示范、Encoding和Post-Encoding工作、具体问题、教师参考、必要支持分支。先只交备课成品供审查，不开展正式教学或修改真实学习进度。

本请求控制当前范围。START_PROMPT 中“开始呈现第一份教学”的通常动作在本次改为交付可审查材料；备课问题不成为用户当前待答任务。原 M0 活动、state/current.md revision22、state/control.md revision11 保持原状。不建立 GoalSpec／PerformanceEvent／Judgment／LearningNeed 或个人课表，不推断 Attention 先验、设备、预算或时间。

## 实际接入与工作责任

已读取本目录 AGENTS、MODEL_ENTRY、FRAMEWORK、START_PROMPT、INTERACTION、当前控制与状态；按当前任务取得共享契约、SK00／session-entry、AG0、AG1、SK01／goal-design、AG2／SK02 与 disciplinary-to-teaching、SK03／design-whole／Encoding／Post、SK05 近期整体路径、SK06／selection-adaptation、AG3 与整体作品评审。原课程粗地图将序列、Attention、条件接口定位于 M5；这只是内容位置，不改变当前 M0 进度或要求用户先完成 M0。

2026-10-11 framework-manifest 的 119 个路径均实际核 SHA-256，未发现缺失或差异。所用方法正文与指纹另见 method-source-fingerprints.json；指纹只说明取得了这些版本，不能证明教学有效。

本次实际有三名备课子 Agent：disciplinary_research 负责学科研究及来源，numerical_material 负责两层算例代码／图／教师运行，reverse_review 在成品之前先形成用途审查基准，再审查成品。主入口负责认知设计、材料／任务／参考、结果采用与交付。它们没有面向用户教学权，没有真实学习进度写入任务；角色文件中的默认“不自动启动”服从宿主本轮主动委派规则。审查不是盲评或真人专业认证；多人返回不作为真伪投票。

## 范围选择

主对象为固定参数的 decoder-only、因果自注意力、追加 token 的推理。覆盖 Q/K/V 运算、逐层缓存等价性与有效前缀、prefill／decode 时序、计算／容量／带宽、优化对象、长上下文能力与证据。MHA／MQA／GQA 是架构比较，不将 GQA 当现有 MHA 的运行开关。

一般 Encoder 双向注意力、Encoder–Decoder cross-attention、训练反向传播、稀疏注意力实现、RoPE 长度扩展算法的完整推导、GPU 内核编写与真实机器人闭环实验暂不展开。它们作为边界或替代出现，不形成新的必修债务。用户正式选定后可从该成品开展教学；本轮只完成备课。

## 保存边界

研究、设计、审查与派生成品在 artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1；题面、学习材料、教师参考与支持分区在 questions/preparation-tests/transformer-kv-cache-20261011；全部可执行学习代码在 code/transformer-kv-cache/preparation-r1。真实状态、会话、目标、评价与计划目录的 63 个既有文件已记录 protected-baseline.json，交付时复核字节与文件集合。教师运行记录为备课核验，不归为用户运行。
