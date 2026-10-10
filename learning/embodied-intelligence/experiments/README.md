# 实验与运行

主代码及可执行 notebook 统一在 [code/](../code/README.md)；每次真实运行在这里建立唯一 run ID，记录精确代码版本、配置、数据生成/split、seed、环境、命令、模型与指标、日志位置和实际结果。运行脚本也放 code/。使用 [实验模板](../templates/experiment.md)。

记录 failed/not_executed 同样有价值；不能写出并未运行的学习曲线、耗时或通过结果。设备、依赖和工具选择按真实条件决定。初始化不安装库、不下载模型或数据，不预设有 GPU。

轨迹任务区分 episode split、训练/验证/测试和 rollout horizon；区分动力学误差、动作误差、闭环表现及延迟。按有效目标设置基线和消融，避免把教学小模型宣称为研究级 WAM。
