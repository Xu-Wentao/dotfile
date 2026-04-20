# Plan: 新增 PyTorch ResNet50 多节点训练 Case

## Context

项目已有两个训练 example（LLM SFT），缺少经典的 CV 图像分类案例。新增 `example-pytorch-resnet-2node/` 展示如何在 Ascend 910B NPU 上做 PyTorch 分布式 ResNet50 图像分类训练（CIFAR-10 数据集），补全 CV 场景的教学覆盖。

## 新增文件

创建 `example-pytorch-resnet-2node/` 目录，包含 4 个文件：

### 1. `train.py` — 分布式 ResNet50 训练脚本
- 使用 `torch.distributed` + HCCL backend（非 NCCL）
- `torchvision.models.resnet50(weights=None)` 从头训练
- `torchvision.datasets.CIFAR10` 自动下载
- 标准 DDP 模式：DistributedSampler 分片数据
- 训练 + 验证循环，rank 0 保存 checkpoint
- 设备用 `torch.device(f"npu:{LOCAL_RANK}")`（非 cuda）
- 命令行参数：epochs/batch_size/lr/output_dir

### 2. `launch.sh` — 容器启动脚本
- 参考 `example-pytorch-1node/launch.sh` 的 NPU 环境 setup
- 参考 `example-mindspore-2node/launch.sh` 的多节点环境变量读取（VC_WORKER_NUM/VK_TASK_INDEX/MASTER_ADDR）
- 关键设置：`HCCL_SOCKET_IFNAME`、`TRANSFORMERS_OFFLINE=0`（允许下载 CIFAR-10）
- 用 `torchrun` 多节点模式启动（非 --standalone）

### 3. `vcjob.yaml` — VolcanoJob 清单
- 参考 `example-mindspore-2node/vcjob.yaml` 的 2 节点结构
- pytorch plugin 注入 MASTER_ADDR/PORT
- minAvailable: 2 gang scheduling
- master + worker 各 1 Pod，各独占 8 NPU
- image 复用 `hiyouga/llamafactory:latest-npu-a2`（已有 PyTorch + torch_npu）
- code-src hostPath: `/data/ascend-train/code/pytorch-resnet`
- outputs hostPath: `/data/ascend-train/outputs/pytorch-resnet`

### 4. `README.md` — 文档
- 配置概览表、文件结构、准备物料、运行步骤、预期输出
- 与 Example A/B 的对比表
- 常见问题排查

## 关键设计决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 分布式后端 | HCCL | Ascend NPU 不支持 NCCL |
| 设备类型 | torch.npu | torch_npu 将 NPU 注册为 npu device |
| 镜像 | llamafactory-npu-a2 | 已有镜像，含 PyTorch + torch_npu |
| CIFAR-10 数据 | 运行时下载 | 体积小（~170MB），不需要预先准备 |
| 训练轮数默认 | 5 epochs | 足够展示收敛，耗时短 |
| 每卡 batch_size | 64 | ResNet50 on CIFAR-10 的标准设置 |

## 验证方式

1. 检查文件格式正确：`python3 -m py_compile train.py`
2. 检查 YAML 语法：`python3 -c "import yaml; yaml.safe_load(open('vcjob.yaml'))"`
3. 与现有 example 对比确认模式一致（vcjob 结构、launch.sh 风格）
