# B3c 通用策略资源

运行资源修订 `pl-strategies/0.1.0`，来源 Encoding 库 v2.0。60张Encoding卡全部编译为完整两载体卡包；另有4份携带完整来源段落的Post条件包。全部64个资源键可直接读取。

先从理解目标与认知工作定位strategy-index.json，再读取选中完整包及conditions；无须一次加载全库。compiled不代表当前课程准入。conditions 为套件新增检查项，未知不按满足处理；exclusion 项已知 false 才表示未触发。教学可提供目标允许帮助；独立证据另核对未被代做的关键操作。

Encoding 包携带 R02 文首与文末规则、D07/D05/N00 覆盖规则、R01 相关完整证据条目。S07/X02 共享补全只是一份实际表现；R09 保留空证据及 H 性质。Post 的有意义键为套件新增，E01—E49 为文献编号、D06 的 P1—P5 为验收编号。

原文件和来源登记不修改。legacy_link_mappings 将旧 outputs 定位映射到当前登记本地来源；完整原文摘录保留原链接，运行按 source_id/locator 及当前映射解析，不依赖另一台机器上的旧绝对路径。

`python scripts/build_b3c_resources.py` 可复现生成；追加 `--check` 只读比较当前产物、原文及登记指纹。manifest.json 含文件与正文指纹。指纹检查与本地正文核对只检测漂移；本轮未外网核论文、未真实教学、未验证方法效果。资源无个人记录，个人配置只进入独立学习工作区。
