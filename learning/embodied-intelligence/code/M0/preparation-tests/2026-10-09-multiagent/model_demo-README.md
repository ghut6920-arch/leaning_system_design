# 视频接口备课的教师核验代码

版本：`2026-10-09-model-demo-v1`。贡献：AI 教师材料 agent 新写，主入口整合；没有学习者贡献、提交或运行。用途仅为 2026-10-09 单模型多 agent 备课审查；不登记正式学习事件。

代码原件：[model_demo.py](model_demo.py)。主材料：[02-materials-demo.md](../../../../artifacts/preparation-tests/2026-10-09-video-interface-multiagent-model-one/02-materials-demo.md)。实际检查结果：[materials-check.json](../../../../artifacts/preparation-tests/2026-10-09-video-interface-multiagent-model-one/materials-check.json)。

本次保留原单元的 `BTHWC=(2,4,2,2,3)` 和 `f=左上角R/G`、`D=2`，重新构造同规格的完整场景轨迹。夹爪和方块的 2×2 RGB 网格是讲解用的人工构造数据，也不倒写为此前实际展示或学习者作品。

依赖只有 Python 标准库。索引字典实现的是轴/逻辑位置和值之间的关系；不模拟 PyTorch storage、stride、view/copy 或 GPU 行为。代码没有导入或安装 PyTorch，也没有训练模型或执行真实机器人。

教师核验运行入口（从学习目录执行）：

```powershell
python -X utf8 'code/M0/preparation-tests/2026-10-09-multiagent/model_demo.py' --check-output 'artifacts/preparation-tests/2026-10-09-video-interface-multiagent-model-one/materials-check.json'
```

运行在本次教师核验中使用 `E:\anaconda\python.exe`。结果文件保存环境版本、代码 SHA-256、全部八帧 RGB、全部八条特征、处理队列与检查结果。`--json` 可将同一结果完整打印；输出文件只覆盖此备课目录内的检查结果。

16 项检查覆盖当前有限构造：完整规格与计数、全部 96 个通道数值在视频路和逐帧路的坐标映射、两路逆映射、错误 reshape 反例、16 个保留左上 R/G 数值的对应、保序特征序列、可信标签恢复与盲 reshape 违例、内容重复而身份不同、其他位置不同而f相同、左上蓝通道碰撞、缺失/重复/越界标签拒绝，以及覆盖完整的标签仍可能为假。每次实际运行成功才称通过；这是教师运行，不是用户运行。

官方 API 核验日期：2026-10-09。官方 stable 地址当次跳转到 2.14 文档，已读相关正文：[torch.permute](https://docs.pytorch.org/docs/2.14/generated/torch.permute.html)、[torch.reshape](https://docs.pytorch.org/docs/2.14/generated/torch.reshape.html)、[Tensor.view](https://docs.pytorch.org/docs/2.14/generated/torch.Tensor.view.html)。文档支持轴重排、等元素数 reshape 及 view 的 stride 条件，不证明本次材料的教学效果。

本次完整输入的枚举检查不证明任意第三方实现、任意视频或实际模型行为。`f` 是明确定义的玩具函数；信息不可逆结论由两个合法 RGB 输入映射到同一输出的反例给出。来源标签的可信性需要生成与传递过程保证，集合覆盖检查不能证明它们真实。
