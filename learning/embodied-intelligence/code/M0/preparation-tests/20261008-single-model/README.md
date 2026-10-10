# 单模型备课的教师核查代码

revision1，2026-10-08，AI 编写，学习者未贡献或运行。关联原视频接口单元的候选备课审查，不是新学习活动。

[verify_materials.py](verify_materials.py) 读取候选包完整输入，调用已有 [标准库参考](../../video_interface_sequence_reference.py)，核坐标、表示变化、来源条件及本地文件保护。没有安装、PyTorch运行、训练或真实设备操作。所有学习可执行代码保留于此 code/ 目录。

运行命令：python -B code/M0/preparation-tests/20261008-single-model/verify_materials.py（从学习目录执行）。实际输出在 [候选包 verification.json](../../../../artifacts/preparation-tests/2026-10-08-video-interface-single-model/verification.json)。脚本写入范围只有该候选结果文件，不更新真实学习记录。

数学/契约来源：本包明确的数据与坐标定义；原标准库参考；官方 permute/reshape 规范由教师另行读取，脚本未执行PyTorch API。完整内容、用途、时间和学习效果边界见候选包。
