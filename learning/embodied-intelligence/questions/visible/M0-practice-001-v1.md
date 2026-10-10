# 活动 EMB-A-M0-PRACTICE-001 / revision 1

prepared，目标 EMB-G-M0-PRACTICE-001 revision1 R1 criterion revision1。

可见输入：artifacts/m0_shape_demo.py revision1。解释：shape是存储各轴大小的元组，不是视频数据本身；total从1开始，for循环依次取每个轴的大小并乘入累计值。
任务：先运行原代码；再把每条视频帧数T从4改为8，其他轴保持不变。修改后先预测total，再运行。回复修改后的shape行、预测值和实际输出；报错则贴完整报错。
资源：提供脚本、Python、计算器；未要求额外安装。核验参考 questions/teacher-reference/M0-practice-001-v1.md，仅后端。
资格：观察按轴修改、预测与运行对照；循环实现由AI代做，不支持自主实现。预测是否真的先于运行在聊天中只能根据实际自报记录。
分支：输出一致且解释可用则进入实际数据轴操作；运行失败则针对真实报错定位最小环境问题；语法陌生则给必要释义再返回同脚本。
停止：用户暂停、预算变化、无新信息或当前操作完成。父任务not_applicable，独立简单实践；初版脚本为AI生成规范产物，用户修改另存不覆盖原件。
预算引用 sessions/2026-10-04-01/raw/entry-001.txt；约60分钟，不声明余额。