# 虚构演示空间

`workspaces` 集中保存 10 个已有开发演示目录：原项目顶层的 9 个 B1—B6 演示，以及原 validation 中的 `b5-demo-workspace`。数据库只做位置移动，原对象、原件、修订和历史记录未改写。

这些都是虚构输入，不能视为真实个人表现或学习效果。实际调用以当前目录为准；历史验收 JSON/TXT 内的旧路径是当时执行事实，继续保留，通过[移动清单](../maintenance/organization-2026-10-04/manifest.json)查找新位置。

查看一个已有空间（从项目根执行）：

```powershell
python -B -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" status
python -B -X utf8 personal-learning-suite/src/runtime/personal_learning.py --workspace "examples/workspaces/B1_虚构演示学习空间" integrity
```

已有空间不重新导入、不覆盖或重放教学。继续维护原演示时先检查当前状态，不能直接使用旧报告里的状态修订号。开发 CLI 及更多示例见[套件说明](../personal-learning-suite/README.md)。
