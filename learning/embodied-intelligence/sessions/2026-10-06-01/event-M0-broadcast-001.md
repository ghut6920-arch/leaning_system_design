# 通道广播原答与反馈 / revision1
活动EMB-A-M0-BROADCAST-20261006-001 revision1；题面questions/visible/M0-broadcast-20261006-v1.md及后台参考同名teacher-reference，均revision1。
实际初答raw/M0-broadcast-001-initial.txt、规范用户代码code/M0/first-session-20261006/submissions/broadcast-001-initial.py revision1已保存读回，未修改或执行。
顺序：上一轮final展示每通道基准/尺度完整示范、广播右对齐规则、y的BTCHW参数shape及新BCTHW任务 → 用户两行代码 → 保存读回 → 当前常规核对。实际额外资源/运行unknown。
用户使用scale/z而非题面gain/out，变量自洽，命名可接受。RGB系数[1,.5,2]正确；参数reshape(1,3,1,1,1)将三项对齐输入v的第二轴C；z=v*scale正确。支持所给规则/范例条件下的BCTHW通道参数构造与逐元素应用；不要求原变量名。
原答未显式注明shape，按已给输入与代码可推scale[1,3,1,1,1]及z[2,3,6,64,64]；该推导由AI反馈给出，不补造用户shape注释或输出。
原答未给绿色0.8的数值结果；拟AI反馈提供0.8×0.5=0.4，不归为用户自主计算。
当前核心代码操作正确，supported/usable用于本段有限教学收束；未支持实际运行、独立恢复规则、G0、保持或整体课程结论。没有新错误依据/必要补课或逐项追问。
拟final确认代码、补shape与绿色值、解释C区分而其他轴共享；写入时反馈未发final，后续按聊天原件核实际帮助。同模型自查，无独立复核；稳定判据/参考及SK04规则复用。
