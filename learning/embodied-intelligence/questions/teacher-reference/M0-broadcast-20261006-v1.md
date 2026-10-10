# 广播参考 / revision1
绑定EMB-A-M0-BROADCAST-20261006-001 revision1，同模型自查，无独立复核。
已读取 https://docs.pytorch.org/docs/2.14/notes/broadcasting.html 410-446（右对齐，相等/1/缺失维度，逻辑扩展）；
https://docs.pytorch.org/docs/2.14/generated/torch.Tensor.new_tensor.html 854（默认dtype/device相同，输入列表复制）。
示范输入[2,6,3,64,64]参数[1,1,3,1,1]可广播，坐标公式z[b,t,c,h,w]=(y[b,t,c,h,w]-baseline[c])/scale[c]。
基准/尺度为教学假设，各尺度非零；(.75-.5)/.25=1、(.25-.25)/.5=0、(.5-.75)/.25=-1。不推出实际数据零均值/单位方差、规范0..1或模型效果。
[3]右对齐最后一轴W，3!=64且都不是1，因此给定示范不可直接相减；W=3能运行也可能语义错误，范围标明。
任务输入BCTHW[2,3,6,64,64]，gain的必要对齐C为第二轴，其余轴共享，可用[1,3,1,1,1]或省略最左B维的[3,1,1,1]；长度1的其他等价表达与正确逐通道索引允许。
gain数据RGB[1,.5,2]，out仍[2,3,6,64,64]，绿色0.8×.5=.4；构造可用v.new_tensor和reshape，允许等价张量构造（dtype/device需相容）。
代码阅读/书面实现只支持给定规则/范例下参数对齐和应用；不推自主恢复规则、真实运行/G0。Python语法检查与PyTorch执行分开记录，当前PyTorch运行未验证。
