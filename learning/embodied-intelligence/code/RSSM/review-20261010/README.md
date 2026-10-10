# RSSM 备课代码与版本

2026-10-10 v1，AI 编写。对应备课：../../../prep/rssm-review-20261010/README.md。

- verify_demo.py：Python 标准库教师数值核查；输入规格为10-model-spec.md及04-tasks.md，输出verification-results.json。
- information-flow.html：无外部脚本依赖的四模式条件关系辅助图，含静态回退；不模拟真实网络或环境。
- check_information_flow.cjs：Node标准库的源脚本/模拟DOM检查，输出information-flow-checks.json；没有操作或渲染真实浏览器。

全部代码与执行结果属于教师准备。没有学习者代码贡献、学习者运行、真实网络训练或环境实验。HTML的实屏布局与实际交互尚未核验，原因见结果原件。

复算：从本目录运行 `python verify_demo.py` 或 `node check_information_flow.cjs`。这些命令只重写同目录的教师结果文件，无需安装依赖。
