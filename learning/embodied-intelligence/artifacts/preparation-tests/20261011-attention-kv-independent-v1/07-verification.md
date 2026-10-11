# 成品核验与范围 v1

日期：2026-10-11。代码由AI编写并运行，全部放在本学习目录code/；无学习者实现或运行。原件与实际输出保留，不使用fixtures、examples数据库或synthetic标志伪装学习记录。下述数值验证仅核机制示范和备课内部数据。

## 框架与真实状态

本次接入已按MODEL_ENTRY核framework-manifest.json：生成日期2026-10-11，119项文件指纹匹配，无不一致。匹配证明取得当前规则版本，不证明学科正确或教学有效；按用途实际读取所选原规则，不宣称已执行所有规则。

备课开始与交付前核对真实状态，SHA-256保持：

| 文件 | SHA-256 |
|---|---|
| state/control.md | `d7ba0aa3bf5c84b0a6888bbcccb48da66ddb7c3dbdc623daf31ff99b44692d87` |
| state/current.md | `0cdb6c945d41f929f66c9d1752403bb47b516e10ddd6fb763e160f84e3719977` |

本次只新增本包与专属code子目录，未写state、goals、plan、assessment或真实学习会话；未读取同单元既有备课／测试记录。当前单元未被登记成真实目标承诺、学习表现或复习需求。

## 实际教师toy检查

原件：[kv_cache_demo.py](../../../code/attention-kv-preptest-20261011/kv_cache_demo.py)；参数与轨迹说明：[代码README](../../../code/attention-kv-preptest-20261011/README.md)；实际JSON：[verification.json](../../../code/attention-kv-preptest-20261011/verification.json)。代码SHA-256：`de7fb5181ceef1b348507cc948c31daafd883e2c5283019701eea4ff5b14b38e`，与JSON记录一致。

解释器E:\anaconda\python.exe，Python 3.12.3，Windows 11；示范自身只用标准库、CPU、固定参数。两层、单头、d=2，每层K/V从本层输入投影；输出包含残差。无RoPE、多头训练、FFN、LayerNorm或语言预测头，不把它称完整语言模型。

| 有限检查 | 实际结果及范围 |
|---|---|
| 五个固定前缀：缓存追加 vs 全前缀重算 | 各历史输出及逐层K/V最大误差0；容差1e−12 |
| 旧K/V固定，新Q改变 | 隔离旧前缀读取的输出差0.102572；排除当前token槽，不冒称完整self-attention单变量实验 |
| 删除旧位置0的KV | 同读出最大差0.299386，示范可见集合改变 |
| 编辑早期token及失效／重建 | 第一层未编辑位置K差0；第二层下游K差0.040617／0.041951。错用旧缓存输出误差0.046408；重建误差0 |
| 双向attention追加 | 旧输出差0.247796；第二层旧K差0.096266，因果前提不能省掉 |
| 容量算术 | 32层、8KV头、128维：BF16 B=1在16k／32k／64k位置为2／4／8 GiB；异长[16384,32768]为6 GiB，填充到同长为8 GiB；均仅payload |

六项有限检查通过。它们支持这些固定参数与输入下的轨迹、层级反例和实现一致性；一般复用资格由01的因果归纳与条件支撑，不由五个前缀外推。没有真实模型精度、任务质量或GPU速度实测。

## 题面、链接与图

成品构建与算术核验原件：[build_review.py](../../../code/attention-kv-preptest-20261011/build_review.py)。它只读取本次新成品、指定策略资源和新toy报告；用Pillow 10.3.0绘静态图。程序图是数值／逻辑呈现，无真实模拟测量。

重新计算服务D的10／18 GiB、工作纸C的6.75 GiB与prompt-only 5.0625 GiB及INT8 3.975 GiB、D0的20.5／15.5／10.5 GiB、I的物理共享比例0.3；题面与教师参考口径一致。D1全部票据是虚构教学材料，不能由这项核验改称实测。

交付前检查本包Markdown本地链接存在，策略正文链接可解析，代码hash与报告相同，六项检查标志均通过；图实际打开检查文字及流程。完整构建核验输出保留于[build-verification.json](build-verification.json)。外部URL实际查阅范围见05，不把本地存在性检查当再次核全网事实。

## 实际采用策略文件指纹

资源版本`pl-strategies/0.1.0`；Encoding原库2.0。具体完整正文读取范围、实例化、反馈／替代／停止及限制见05；下表指纹用于版本定位，不表示已执行整卡训练。

| 文件 | SHA-256 |
|---|---|
| encoding/S05.json | `75be952e8bc57ae87fe6d228cf1097f7dcf8db591987794578324c757fbeca36` |
| encoding/R06.json | `bf99f2ad28c2871ea3ea20d63fc9adb41f85ccef326488da9ac405d3a645b1bf` |
| encoding/D04.json | `c8757b56e85a06e45d62e6c70e9acbf7393756364eca737cfd7470d899ffd832` |
| encoding/R10.json | `16612c0a90f4a9fafe9f8e2e1da6f27d055ce0feed55cd56155433c4a147e597` |
| post/retrieve-relation.json | `9a40c98a6eddedc06cab02155aed54480c242f3f7bd2bbf70e116a0c87ec2dbc` |
| post/select-method.json | `b33844944758174619f882a3131a60f3367782fcf88a94e3f2cb00eab2d022b8` |
| post/conditional-update.json | `dd9ff6021b01147af7e8d51d610f1e5ba3174ccf7d0061903462f4ec2f4e9874` |

尚未执行正式教学、真实原答保存、实际GPU基准、生产混合负载、学习者个体适配或延迟后测。所备材料与支持可供审查，效果与实际工程采用仍没有对应证据。
