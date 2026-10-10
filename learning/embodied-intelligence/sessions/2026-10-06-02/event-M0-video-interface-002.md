# 整体接口初答与修订事件 / revision2

单元EMB-U-M0-VIDEO-20261006-02 revision1；目标goals/M0-video-interface-first-20261006-02.md revision1。上一轮final已实际展示第二段：原BTCHW合法合并B/T、k=b*4+t完整范例、摄像头新输入BTHWC及双接口整体任务。范例使用b=1/t=2/k=6。用户对应本轮原答raw/M0-video-interface-002-initial.txt revision1已保存读回。口述PBCTHW/NCH/图针等按原文保留，不据转写措辞诊断能力。
常规限定判断：逐帧线合并B/T的思路有支持，但当前BTHWC若仅合并会得到NHWC，尚缺C轴重排；视频线只交换第二/第三轴得到BHTWC，与目标BCTHW不符，所说最终BTCHW亦不符。用户未给两条具体数值shape或身份保持说明，整体工作尚未完成。不能据此推一般张量基础弱，先对齐本题改变的输入规格；不追加基础语法微题。
拟本轮final帮助：明确起点BTHWC=[2,4,2,2,3]；给视频线BTHWC→BCTHW=[2,3,4,2,2]及逐帧线BTHWC→BTCHW=[2,4,3,2,2]→NCHW=[8,3,2,2]；说明先合并B/T再把C移到N后也合法。该帮助代做两条路线和shape，之后不归用户自主构造。尚待学习者解释两路的身份保持，以及合并图像如何对应回原视频/帧，沿同一说明继续；允许查看已经提供的规则。与已备整体任务同一要求，不新增单元/补课队列。
初答记录写入时上述帮助和后续解释工作prepared_for_final；之后已由上一轮final实际展示两路纠正、shape、合法替代路线及k映射，再收到同一说明的修订。

修订原件raw/M0-video-interface-002-revision-001.txt revision1已保存读回，仍为同一事件。视频路线重排轴、保留要素的说明方向正确；逐帧路线认识C重排与B/T合并，但“里面元素也变了”需区分组织/数值，未据此确诊固定误概念。口述“B和7”保留原文，按本题B/T语境解释，不以转写诊断。
本轮拟展示questions/backup/M0-video-interface-identity-20261006-02-v1.md revision1中的数值/总数保持、两级编号合并和逆映射解释；prepared_for_final，未预记本轮实际展示。解释后不追加同类复述微题；完整理由与逆映射由AI给，不补记学习者独立掌握或自主修订。当前有限教学主线可收束，未证能力是结论边界，不新增补课/未来日期。预算/环境unknown，控制revision10不变；G0、实现/运行/整体独立通过未裁定。同模型自查，无独立复核。
