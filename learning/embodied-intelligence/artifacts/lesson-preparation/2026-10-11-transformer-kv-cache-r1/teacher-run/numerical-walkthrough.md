# 连贯数值示范及教师说明 / preparation-r1

用途：备课审查的实际材料。下列是 AI 教师运行固定 toy 的结果，不是学习者作答、运行或理解表现。原件 `code/transformer-kv-cache/preparation-r1/kv_cache_demo.py`；机器可回查结果 `checks.json`、完整运行文本 `stdout.txt`、逐步表 `trace.csv` 均在本目录。演示对象为普通 causal decoder 的全前缀重算与逐层 KV 重用；性能只记录逻辑工作量。

## 1. 先分清输入、预测与缓存时刻

用输入 token ID `[1,4,2]` 代表位置 0、1、2。它们是 toy 的固定 ID，没有自然语言语义。Prefill 后两个层的 K/V 各有 3 行：位置 `[0,1,2]`。最后一个输入 token 的 logits 用于预测位置 3 的 token。演示指定位置 3 token 为 5，以固定后续比较对象；这个 ID 的选择不是 argmax 输出。此刻位置 3 的 KV 尚未生成。

下一次 forward 输入 token 5、绝对位置 3。每一层从当前新行状态得到 Q₃、K₃、V₃，把 K₃、V₃ 加到这一层 cache，Q₃ 对这一层位置 0…3 的 K/V 做 attention，再把得到的新隐藏状态传到下一层。其 logits 用于预测位置 4。因此生成 token 的选择和该 token 被模型再次处理、写入 KV 发生在相邻的两个时刻。

## 2. 用同一序列比较完整路径和增量路径

继续固定输入位置 4、5、6 的 token 为 `[0,6,3]`。每次增量结果都与从原始 token 前缀重算所有层的结果比较，容差 `1e-12`，环境数值为 Python binary64 float。

| 本次输入 | 本次输入位置 | 每层 cache 长度 | 两路径最后 logits 最大差 | 旧 K/V 保持原值 | 这次 logits 预测位置 |
|---|---:|---|---:|---|---:|
| prefill `[1,4,2]` | 0、1、2 | `[3,3]` | 0 | true | 3 |
| 5 | 3 | `[4,4]` | 0 | true | 4 |
| 0 | 4 | `[5,5]` | 0 | true | 5 |
| 6 | 5 | `[6,6]` | 0 | true | 6 |
| 3 | 6 | `[7,7]` | 0 | true | 7 |

这四次追加的所有 cache K/V 也与完整前缀对应 K/V 相同，最大差为 0。相同是本例实际输出；一般实现比较应使用容差，不能把“任意硬件/核函数必定逐 bit 相同”作为正确性定义。

因果机制：旧位置 i 的状态只能依赖位置 ≤ i。追加未来 token 不改变这些依赖；按 token 的 LayerNorm/FFN 也不把新行混入旧行统计。第 2 层 K/V 是第 1 层 contextual hidden state 的投影，仍满足这个因果边界。每层保存旧 KV，可以只做新 token 的行计算。

适用条件：同一模型参数、完整相同前缀、相同绝对位置/位置处理、相同可见 key 集、确定性推理、相同数值语义。本例采用 eval 式无 dropout 的固定模型；不由本例推出训练时随机路径等价、不同模型/前缀 cache 可混用或截断 cache 仍保持原全上下文函数。

## 3. KV 可重用，attention 权重需要重算

独立的 attention 子层局部例子，单头、head dimension=1，因此缩放因子为 1；这不是上述两层模型某一层的同参输出。给新 query `q=ln2`、keys `[1,0,1]`、values `[2,6,10]`。

scores 为 `[ln2,0,ln2]`，exp scores 为 `[2,1,2]`；归一化权重为 `[2/5,1/5,2/5]=[0.4,0.2,0.4]`。输出 `0.4×2+0.2×6+0.4×10=6`。

只有旧两项时，同一个 q 的权重是 `[2/3,1/3]`，输出 `2/3×2+1/3×6=10/3`。新增 key/value 已使归一化分母改变；未来 query 一般也不同，因此旧 query 的权重不能直接当作新 query 的权重。保留的是每层 K/V，当前 query 的分数与 softmax 仍计算。

## 4. chunked append 的 mask 要对上绝对位置

已有 3 个 token 的 cache，一次输入两个新 token `[5,0]`。每层 `Q.shape` 在本例为 `[q_len=2,Hq=2,dh=2]`，`K/V.shape` 为 `[key_len=5,Hkv=2,dh=2]`（代码用 Python list；这里只解释逻辑形状）。query 绝对位置为 3、4，key 为 0…4。

| query \ key 位置 | 0 | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|---:|
| 3 | 1 | 1 | 1 | 1 | 0 |
| 4 | 1 | 1 | 1 | 1 | 1 |

条件是 `key_absolute_position ≤ query_absolute_position`。结果与完整 5-token forward 的位置 3、4 logits 均相同，最大差为 0，原 3 行 KV 不变。直接按局部行列号对整个 2×5 score 矩阵套左上三角会让第 1 个 query 只看到 key0、第 2 个只看到 key0、1；本例错误结果最大 logits 差 `0.07359257574200351`。

## 5. 实际失败对照与修复

| 改动 | 正确比较对象 | 实际最大 logits 差 | 教师解释与修复 |
|---|---|---:|---|
| prompt 从 `[1,4,2]` 改成 `[1,6,2]`，仍复用原 3 行 cache 再处理 token5 | 新前缀 `[1,6,2,5]` 的完整结果 | 0.023334534953964425 | cache 所表示的前缀已错；从最后未变边界按各层重建受影响的 cache，本例简单重算整个新 prompt |
| 位置 3 新 token 错用 PE(0)，causal mask 与 cache 位置仍正确为 3 | 原 `[1,4,2,5]` 完整结果 | 1.2167654985176246 | 位置编码是模型输入函数的一部分；恢复 PE(3) |
| 各层删除位置 0 KV，保留其余绝对位置，不补回 | 原全上下文结果 | 0.02713883507148207 | 少了可见 key/value，函数变了；恢复丢失 KV 或明确使用另一个受限上下文机制 |

前缀 edit 对比同时显示：未改 token 位置 2 的第 1 层 KV 差为 0，第 2 层 KV 最大差为 `0.02410763630481827`。第 1 层 KV 的输入是当前位置 embedding+PE；第 2 层 KV 的输入已混入第 1 层前缀 attention。所以“只修改被编辑 token 的各层 cache，其余行都保留”一般无效。重建新 prompt cache 后再 append token5，最后 logits 与新前缀完整结果差为 0。

这些是固定参数和输入的可回查反例。存在退化参数、某些 value 相同或后续层抵消时，某一次编辑/删除也可能不改变 logits；不能用这里非零结果证明所有模型所有输入必然不同。

## 6. 省下的是哪些计算，留下了什么负担

本例比较长度 3、4、5、6、7 的五次 forward 观察；两层、每层两 query 头。

| 逻辑计数 | 每次完整前缀重算 | prefill 一次后逐 token append |
|---|---:|---:|
| 每个 Q/K/V 投影分别的 token 行数（跨两层） | 50 | 14 |
| Q+K+V 投影 token 行数合计 | 150 | 42 |
| 理论 dense score 元素数（跨层、头） | 540 | 124 |
| mask 有效 causal score 元素数（跨层、头） | 320 | 112 |

累计的有效 query-key 配对减少，但 decode 新 query 仍要与已有各 key 比较；上下文增长使当前步的读取/score 规模继续增长。逻辑计数不等于实际 kernel FLOPs、wall time、吞吐或显存测量；本 Python toy 无法得出生产 GPU 性能。

逻辑 cache 容量 `M=2 L B T Hkv dh s`。`L=32,Hq=32,dh=128,T=32768,B=1,s=2 bytes`：MHA Hkv32 为 16 GiB，GQA Hkv8 为 4 GiB，MQA Hkv1 为 0.5 GiB。GQA 同时把 T 增到 65536、B 增到 2，容量增到 16 GiB。因子 2 表示 K 和 V，不要再多乘一次；Hq 不是这里的 cache 头数。该公式不计参数、激活、padding、allocator、页/元数据和量化额外信息。

配图原件：`../figures/cache-timeline.svg`、`../figures/two-layer-dependency.svg`、`../figures/kv-capacity.svg`。它们分别解决生成/缓存时刻、跨层上下文化与头数/容量的必要关系；无需要求学习者重新画出图片才能使用材料。
