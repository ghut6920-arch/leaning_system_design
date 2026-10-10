# 视频预处理原答与反馈 / revision1
活动EMB-A-M0-PREPROCESS-20261006-001 revision1。合法题面questions/visible/M0-preprocess-20261006-v1.md，后台参考questions/teacher-reference/M0-preprocess-20261006-v1.md revision1。
原话raw/M0-preprocess-001-initial.txt revision1已写入读回；用户代码字节原件code/M0/first-session-20261006/submissions/preprocess-001-initial.py revision1已写入读回。用户贡献为三行及原注释，没有改写/执行。AI纠正版另存code/M0/first-session-20261006/preprocess_correction.py revision1。
时间线：上一轮final实际给完整prepare_video/索引范例、函数含义、float与除255条件及题目 → 用户三行原答 → 保存读回 → 当前同模型常规核对。实际外部帮助/执行unknown。用户未提交修改过的函数定义，核对按已展示prepare_video定义。
本题目标输入BTHWC→输出BTCHW。原调用prepare_video按已展示函数输出BCTHW[2,3,6,64,64]；原注释对这份示范函数输出正确，但不满足题目目标[2,6,3,64,64]。需要改布局转换为原轴(0,1,4,2,3)，仍转float并按给定条件/255。
frame仍使用示范变量x而非本题产生的y，当前三行未连接成依赖y的接口；不凭缺上下文断言x必然未定义。B=1/T=4在旧BCTHW布局索引位置正确，显示对应第2视频第5帧的计数规则；在目标BTCHW中应frame=y[1,4,:,:,:]。
RGB保留C轴，形状[3]正确；用空间坐标11/21取的是第12行第22列，不符题目第11行第21列，需要10/20。原坐标合法，不是越界错误。
有限判断：原代码没有满足完整目标接口；旧布局下B/T零起始计数及取RGB保留通道受支持，目标布局转换、连续变量连接、指定像素位置observed_not_met；不推一般能力、心理原因、程序运行或G0。
拟final给三点解释和完整AI纠正版。写入时未发final，不补记用户自主修订；原答/关键帮助/后续修订保留同一事件。完整修复代码由AI提供，仅为教学支持，不作为用户自主实现证据。
稳定目标/参考/已读SK04证据规则复用，同模型自查，无独立复核。当前提供可靠纠正后收束，不增加逐行微测或额外补课队列；进一步完整应用仍需真实新作品。
