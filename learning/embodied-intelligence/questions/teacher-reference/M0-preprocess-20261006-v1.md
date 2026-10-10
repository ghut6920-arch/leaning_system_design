# 预处理教师参考 / revision1
同模型自查，非独立复核。绑定EMB-A-M0-PREPROCESS-20261006-001 revision1。
要求依据原大纲M0.2与当前有限代码接口应用；新增uint8/float/缩放为AI提供的必要输入，不先测未知定义。资料为教学规格，不描述实际相机采样。
已实际读取：
https://docs.pytorch.org/docs/2.14/generated/torch.permute.html 1079/1086；
https://docs.pytorch.org/docs/2.14/tensors.html 3760-3768；
https://docs.pytorch.org/docs/2.14/generated/torch.Tensor.float.html 854：float()相当于转float32。
https://docs.pytorch.org/docs/2.14/type_info.html 3764-3771：整数类型数值属性。uint8为无符号8位整数，范围0..2^8-1=255。
算术检查0/255=0、255/255=1；128/255≈0.50196、64/255≈0.25098。缩放条件必须输入0..255且目标0..1；float()本身不归一化，不宣称所有模型相同规格。浮点表示有舍入误差，不作无损可逆性声称。
示范input BTHWC→BCTHW，原轴0/4/1/2/3正确；frame固定B0/T2，rgb固定H10/W20，均在轴域内。全批147456标量不变。
参考解：y=camera.permute(0,1,4,2,3).float()/255.0，shape[2,6,3,64,64]；
frame=y[1,4,:,:,:]，shape[3,64,64]；
rgb=frame[:,10,20]，shape[3]。
允许分步赋值、等价索引及有序规格；若仅文字/未写代码，只判断对应与解释，不记独立实现。允许参考示范，写对仅支持这些输入帮助下的连贯应用；不推软件运行/G0/保持。
没有安装/执行PyTorch，也不把教师示范当用户实现。代码语法检查另据实际命令，不等于PyTorch输出验证。
