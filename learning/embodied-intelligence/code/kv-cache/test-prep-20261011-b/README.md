# KV Cache 教师演示 / version 1.0.0

作者与贡献：AI mechanism_audit 子 Agent 于2026-10-11独立编写；用户授权测试备课；没有学习者代码或学习者运行贡献。本目录为规范代码原件，研究稿与备课包引用本原件，不复制成其他可执行路径。

`demo.py` 仅用 Python 标准库。两层、单头、d=4；各层固定 WQ/WK/WV；Q/K使用逻辑位置的RoPE，base=10000、相邻坐标对；V不旋转；每层位置局部残差与非线性为 `tanh(hidden + attention)`。完整重算路径对各层所有位置重新计算；增量路径只计算新位置并保存各层旋转后K和V。允许keys的切片代表因果mask，而非用0/1乘法把score归零。

六个固定输入前缀逐一核对最后位置hidden，以及所有层完整K/V，允许最大绝对误差1e−10。三个负例须实际产生大于1e−5的差异：改旧前缀仍用旧cache；把新token逻辑位置从4重置为0；把全注意力cache直接裁掉早期两位置但仍与原full attention模型比较。负例只展示当前数值例的失效，不概括所有位置变换或原生window模型。

容量核验是另一个32层GQA模型的解析payload算术，与两层toy的训练能力无关：L32/Hkv8/d128/BF16每元素2bytes，128KiB/token；32768-token四路16GiB；FP8一字节payload四路8GiB。给定cache系统12GiB、预留1GiB，11GiB raw预算下BF16 floor cap2、FP8 payload-only floor cap5；真实scale/残留、页表、allocator与峰值仍需核查。脚本不实现FP8、不测质量或硬件速度。

运行入口（从学习目录执行）：

```powershell
python code/kv-cache/test-prep-20261011-b/demo.py
```

默认输出为 `artifacts/test-prep/kv-cache-20261011-independent-b/teacher-check-output.json`。输出记录Python版本、实际执行时刻UTC、代码SHA-256及version；按具体sha定位此次代码字节。重新运行会刷新该教师核验输出。课堂发生、学习者表现与学习进度均不由本输出证明。

依据和读取范围详见本学习目录 `materials/test-prep/kv-cache-20261011-independent-b/mechanism-analysis.md` revision1；核心原件：

- [Attention Is All You Need §3.2](https://arxiv.org/html/1706.03762v7)：scaled dot-product与因果屏蔽。
- [RoFormer §3.2](https://arxiv.org/html/2104.09864v5)：逻辑位置Q/K旋转。
- [HF How caching works](https://huggingface.co/docs/transformers/cache_explanation)：逐层K/V cache与新位置运算；页面的mask乘法式不复制。
- [HF float mask语义](https://huggingface.co/docs/transformers/attention_interface#pass-a-custom-4d-attention-mask)：允许0、屏蔽−∞，在softmax之前相加。

实际执行：2026-10-11，以Python3.12.3运行并读回输出。六个prefix最后hidden和全部层K/V最大误差均0；三个负例max error依次约0.151760、0.010892、0.109371。输出记录代码SHA-256为 `d5e3cb6c71ee9498685cd7bfe843c3c0ffdca69fbf48b1f7dd45ba8b0e111b93`。

当前限制：这是自制小模型，没有tokenizer、训练、词表logits、GPU kernel、分页、offload或量化实现。双精度Python浮点有限样本通过不证明所有Transformer实现正确；负例差异不代表任何真实任务质量降幅；程序无计时逻辑，不得推断性能倍数。
