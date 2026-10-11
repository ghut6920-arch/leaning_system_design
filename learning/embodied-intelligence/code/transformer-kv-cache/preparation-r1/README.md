# KV Cache 备课数值材料 / preparation-r1

本目录为 2026-10-11 的 AI 教师备课代码，不是学习者作品、训练模型或学习者运行记录。版本为 `preparation-r1`；全部可执行内容仅位于本 `code/` 子目录。AI 贡献：完整编写标准库 toy decoder、数值验证、结果记录与 SVG 生成。未安装依赖，没有调用 PyTorch。

运行原件：`kv_cache_demo.py`。在学习根目录运行：

```powershell
python code/transformer-kv-cache/preparation-r1/kv_cache_demo.py
```

解释器已实际定位到 `E:\anaconda\python.exe`；运行的 Python 版本、平台和解释器路径保存于 `teacher-run/checks.json`。Python `float` 在该环境采用 binary64；正确性比较容差 `1e-12`。参数由标准库 `random.Random(20261011)` 固定初始化；输入 prompt `[1,4,2]`、延续 `[5,0,6,3]` 固定，不依据 argmax 选择，所以两条计算路径不会因预测分岔而改变比较对象。

模型包含两层 causal MHA decoder：`d_model=4, Hq=Hkv=2, head_dim=2`，绝对 sinusoidal 位置编码，从位置 0 开始；每层含按 token 的 pre-LayerNorm、Q/K/V/O 投影、残差和 FFN，最后 LayerNorm 与词表 logits。权重固定、无 dropout、无训练。第 2 层 K/V 来自已受第 1 层 attention 影响的上下文化状态，而非单纯复制 token embedding。

完整前缀路径每次从原 token 序列和空 cache 重算所有层；增量路径只输入新 token 并逐层读取/追加 K/V。两条路径共用标量数值算子，使比较只改变复算范围和 cache 使用。比较每个延续步骤的最后 logits、所有 K/V、旧 cache 行不变性。Prefill 末 logits 用于预测第一个生成 token，其位置尚未写入 cache；后续将该 token 输入模型才写入。

另有 `q_len=2, old_cache_len=3` 的 chunk append：每层真实 mask 为 `[1,1,1,1,0]` 与 `[1,1,1,1,1]`，以绝对 query/key 位置定义。负例分别是前缀修改后继续使用旧 cache、保持 causal 位置却错误使用 PE(0) 替代 PE(3)、保留绝对索引但删除位置 0 的 K/V、直接对矩形布局套局部左上三角 mask。这些实际输入出现差异，仅提供反例，不声称所有修改/删除在任何参数下必然改变输出。

单头手算对照使用另一组局部参数 `q=ln2, K=[1,0,1], V=[2,6,10]`，权重 `[0.4,0.2,0.4]`、输出 6；只对旧两项重新归一化得输出 `10/3`。这解释为什么可保存 K/V，但对未来 query 不能直接沿用此前 attention 权重；该局部例子不冒称为两层模型的某一组投影数值。

逻辑工作量记录针对前缀长度 3、4、5、6、7 的五次 logits 观察。`projected_rows_per_Q_K_V` 是跨两层汇总的 token 行数，对 Q、K、V 各自相同；`Q_K_V_rows_total` 再乘 3。`dense_scores` 计理论矩形 score 元素；`valid_causal_scores` 计 mask 允许的 score 元素，两者均跨两层、两 query 头汇总。它们不是 wall time、FLOPs、显存测量或 kernel 性能证明。

输出固定在学习根目录的 `artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/teacher-run/` 与 `figures/`。程序写出 `checks.json`、`stdout.txt`、`trace.csv`，读回 JSON/stdout 检查一致性，并检查三张 SVG 是合法 XML。复跑只覆盖本版本备课输出，不修改 `state/`、`plan/`、`sessions/`、`assessment/` 或任何 learner event。

容量公式 `2 L B T Hkv dh bytes_per_element` 是所有层的逻辑 K/V 元素容量。假设每条序列长 T、同一精度与 KV 头数，FP16 每元素 2 bytes；不计模型参数、激活、padding、allocator、页和元数据、量化尺度等。`L=32,Hq=32,dh=128,T=32768,B=1` 时：MHA Hkv32 为 16 GiB，GQA Hkv8 为 4 GiB，MQA Hkv1 为 0.5 GiB。同一 GQA 在 T65536、B2 时为 16 GiB。

概念来源：Transformer 原始 attention 定义 [Vaswani et al., 2017](https://arxiv.org/abs/1706.03762)；每层自回归 KV 重用与生成循环参考 [Hugging Face cache explanation](https://huggingface.co/docs/transformers/cache_explanation)；GQA 概念和缓存头数区分参考 [Ainslie et al., 2023](https://arxiv.org/abs/2305.13245)。这些来源用于机制依据，本数值例子和图是 AI 自建。主备课资料中的来源核验记录由主代理整理。

## SVG 的 PNG 复现渲染

渲染代码原件为 `render-figures.cjs`（AI 编写）。使用宿主 bundled Node.js 与 bundled sharp，无安装；默认 sharp 原件为 `C:/Users/15006/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.cjs`，可通过 `--sharp-module` 指定另一个绝对模块路径。实际 Node 可执行原件为 `C:/Users/15006/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`。

在学习根目录复现：

```powershell
& 'C:/Users/15006/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' 'code/transformer-kv-cache/preparation-r1/render-figures.cjs'
```

三张 SVG 按 density144 渲染为同目录同名 PNG；图中文字保持 SVG 指定的 Microsoft YaHei / Noto Sans CJK SC / sans-serif 系统字体解析。程序逐张读取输出 PNG 的格式、尺寸与字节数，并写出、读回 `figures/render-info.json`，记录实际 Node/sharp/libvips 版本及绝对路径。PNG 是白底静态教学材料，渲染不修改模型代码或真实学习记录。

仅更新 cache 时间线文字时，先运行 `python code/transformer-kv-cache/preparation-r1/kv_cache_demo.py --refresh-cache-timeline`，再在上述 Node 渲染命令末追加 `--figure cache-timeline`。此路径只重出目标 SVG/PNG 并更新其 render-info 记录，保留其它图和机制数值结果。

## 备课汇编与文件核验

`build-delivery.ps1` 由主入口 AI 编写，属于本版本备课代码。它核对开始时保留的63个真实学习记录文件及集合、119个框架指纹，汇编完整审查稿并读回，检查本地 Markdown 链接，保存交付清单与检查结果；不执行教学、不写学习进度。可在学习根目录运行该脚本。数值与图像检查范围仍以上文及交付核验说明为准，汇编不重复声称验证学习效果。
