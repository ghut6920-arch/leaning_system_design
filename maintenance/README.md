# 项目维护记录

2026-10-04 的目录整理将原顶层 57 份文档分为八类，并把 10 个虚构演示数据库集中到 examples。运行套件保持当前位置与内部依赖结构。

- [移动与变更清单](organization-2026-10-04/manifest.json)：旧路径、新路径、整理前文件指纹、19 份来源登记前后值以及引用修正记录。
- [原始备份](organization-2026-10-04/before-organization.zip)：开始移动前的文档、运行套件与演示数据库；不包含可再生成的 Python 缓存。维护工具本身也在快照中。
- [保存与链接检查](organization-2026-10-04/verification.json)：全部纳入快照的原文件仍存在，10 份数据库和 170 份历史原始结果字节保持，全项目本地断链为 0。
- [存储与备份检查](organization-2026-10-04/storage-check.json)：10 份 SQLite 只读 quick_check 与 ZIP 的 CRC 检查均通过。
- [缓存清理](organization-2026-10-04/cache-cleanup.json)：仅删除 3 个 `__pycache__` 目录中的 30 个可再生成文件，没有删除文档或数据库。

原研究报告引用的 `Encoding研究与策略库.html` 在整理前已缺失。该引用现在明确注明“未随本项目提供”，没有制造替代文件；原链接仍可从备份回查。来源的路径／链接变化已经登记，并重建运行资源；这不改变研究结论，也不构成新的外部文献核验。

目录归类后的[完整回归](../personal-learning-suite/validation/folder-organization-2026-10-04/all-runtime-report.json)为 483/483，98.032 秒；失败、错误、跳过均为 0。[逐项输出](../personal-learning-suite/validation/folder-organization-2026-10-04/all-runtime-output.txt)与[静态报告](../personal-learning-suite/validation/folder-organization-2026-10-04/static-report.json)另存；静态为 32/32，19 份来源通过。原 B0—B7 与架构审计修复报告保留，不覆盖。运行服务、Agent／Skill 职责和教学判断规则未修改。

整理辅助工具为[reorganize_project.py](../personal-learning-suite/scripts/reorganize_project.py)。`prepare` 和 `migrate` 用于本次一次性规划／引用迁移，不要在完成后的项目上重复运行；只读文件核查可重新执行 `verify`，它会更新本次核查报告。目录移动与缓存删除均使用已核对项目边界的 PowerShell 原生命令。
