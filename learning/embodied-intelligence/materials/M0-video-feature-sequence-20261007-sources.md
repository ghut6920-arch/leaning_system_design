# 接口收束与特征序列材料依据 / revision1

维护备课，原目标及评分标准未修改。原始资料仍为M0视频接口目标、teacher-reference/M0-video-interface-20261006-02-v1、两份原答事件及末轮实际解释。新增表示来自本题明确给定的逐帧函数契约，不是新采样或学习者输出。

2026-10-07实际核对官方 [permute规范](https://docs.pytorch.org/docs/2.14/generated/torch.permute.html)和 [reshape规范](https://docs.pytorch.org/docs/2.14/generated/torch.reshape.html)：前者按给定轴顺序组织视图；后者同元素数重组形状，不能依赖其一定复制或一定为视图。PyTorch参照与本题明示坐标映射一致，用户本地版本未确认。

标准库实现使用相同数学映射和显式帧标签，教师已实际运行 [核查代码](../code/audits/test_video_interface_sequence.py)；[结果](../experiments/M0/video-interface-sequence-teacher-check-20261007.json)为9项通过、1项PyTorch运行因缺库未执行。正向／标签恢复在15组B/T尺寸及合法行置换中核对，错误／重复／缺失标签和未知顺序拒绝完整恢复。PyTorch代码仅语法和当前规范核查，未声称实际运行，不自动安装。

源代码：[标准库](../code/M0/video_interface_sequence_reference.py)、[PyTorch参照](../code/M0/video_interface_sequence_torch.py)。教师构造唯一编号值用于核对身份，不表示现实像素具有可反推帧号的数值规律。玩具编码器仅取两个通道值，没训练、不跨帧、不置换行；改变未选蓝值而输出不变，说明不能据向量还原全部图像。

代码结果只支持这些契约下的教师参考；不属于学习者实现／运行／测试选择、真实视觉性能或世界模型实验。原R3的目标内工作承接到同一说明，数据／环境、保持和迁移未知仍保留。策略正文及正式C0／Encoding／Post／计划收束依据沿本次teacher-reference；新的完整Post选用包已实际读取相关规则及11段原文，借用部分与可作结论分开。
