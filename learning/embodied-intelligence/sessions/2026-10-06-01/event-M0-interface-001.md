# 视频接口原答与反馈 / revision1
活动EMB-A-M0-INTERFACE-20261006-001 revision1；题面questions/visible/M0-interface-20261006-001-v1.md及后台参考questions/teacher-reference/M0-interface-20261006-001-v1.md revision1。
原答raw/M0-interface-001-initial.txt revision1已原样保存读回。原答三行不覆盖，修订仍为同一事件。
实际顺序：上一轮本聊天final展示索引规则、固定B/T取帧的完整例子、原轴B0/T1/C2/H3/W4、一次permute示范及有语义表头的reshape对照 → 用户当前初答 → 保存读回 → 当前核对。外部帮助/实际代码运行unknown；无用户执行记录。
判据核对：新shape[2,6,64,64,3]正确；转换后固定B/T的帧shape[64,64,3]正确。轴序初答(0,1,4,5,3)错误：五个原轴编号只到4，其中5无对应原轴；合法目标[B,T,H,W,C]应对应(0,1,3,4,2)。
有限判断：给定定义/示范条件下的新shape和帧shape supported/usable，原轴编号参数映射 observed_not_met/usable。只说明本题原答，不推稳定误解或Python能力；正确形状不能代替正确permute参数。G0/独立实现/运行/保持未支持。
拟本轮final提供对应B0/T1/H3/W4/C2及正确序列(0,1,3,4,2)，此修正由AI提供，不补记用户自主修订或全部正确。写入时尚未final展示，后续从聊天确认。
反馈后收束，不要求重复抄写或追加逐轴微测。实际独立参数应用尚未证实，今后整体接口实践有实际需要时再观察，不建额外补课债务。
同模型常规自查，无独立复核。既有SK04/evidence-rules和教师参考复用，没有变更目标/判据/授权。
