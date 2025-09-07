# PCB训练系统使用说明

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 快速测试
```bash
python quick_start.py
```
选择选项1进行系统测试

### 3. 启动完整系统
```bash
python main.py
```

## 系统组件

### 1. 文件监听器 (`文件监听.py`)
- 监听 `txt标注/` 目录下的TXT文件
- 自动解析产品信息和检测结果
- 将图片分类到 `output/` 目录

### 2. 训练目录监听器 (`训练目录监听.py`)
- 监听 `output/` 目录下的产品文件夹
- 当数据量满足要求时自动触发训练
- 要求：OK图片≥130张，NG图片≥50张

### 3. 训练系统 (`pcb_training_system.py`)
- 基于Anomalib的异常检测训练
- 支持SuperSimpleNet模型
- 自动保存训练结果和模型文件

### 4. Web监控界面 (`web_interface_enhanced.py`)
- 访问地址：http://localhost:5001
- 实时监控训练状态
- 查看训练结果和下载模型

## 目录结构

```
PCB_Defect_Detection/
├── txt标注/           # TXT标注文件输入目录
├── 图片数据/          # 原始图片数据目录
├── output/            # 整理后的数据目录
├── data/              # 训练数据目录
├── training_results/  # 训练结果输出目录
├── trained_models/    # 统一的模型权重存储目录
│   ├── 产品号_元件名_supersimple.ckpt
│   └── 产品号_元件名_supersimple_info.json
└── logs/              # 系统日志目录
```

## 数据格式要求

### TXT标注文件格式
```
ModelName: 产品型号
ConfirmedResult: P (正常) 或 F (异常)
```

### 图片文件命名
```
BR1_条码号__位置.jpg
例如: BR1_2040353325__1.jpg
```

### 训练数据结构
```
产品号_元件名/
├── train/
│   └── OK/          # 训练用正常样本
└── test/
    ├── OK/          # 测试用正常样本
    └── NG/          # 测试用异常样本
```

## 配置文件

### 模型配置
- `configs/model/supersimple_pcb.yaml` - SuperSimpleNet模型配置
### 触发配置
- `configs/trigger.yaml` - 训练触发阈值

### 数据配置
- `configs/data/pcb_folder.yaml` - 数据加载配置

## 常用操作

### 手动添加训练任务
```python
from pcb_training_system import add_training_task

# 普通训练（会检查已有权重）
task_id = add_training_task(
    name="产品号_元件名",
    data_root="/path/to/data",
    model_type="supersimple"
)

# 强制重新训练（忽略已有权重）
task_id = add_training_task(
    name="产品号_元件名",
    data_root="/path/to/data",
    model_type="supersimple",
    force_retrain=True
)
```

### 权重管理操作
```python
from pcb_training_system import check_model_exists, get_model_info, list_all_models

# 检查模型是否存在
exists = check_model_exists("2150155000_PC1", "supersimple")

# 获取特定产品的模型信息
model_info = get_model_info("2150155000_PC1", "supersimple")

# 获取产品的所有模型
all_models = get_model_info("2150155000_PC1")  # 返回所有模型类型

# 列出所有已训练的模型
models = list_all_models()
```

### 查看训练状态
```python
from pcb_training_system import get_queue_status, get_all_tasks

# 查看队列状态
status = get_queue_status()
print(f"队列中任务数: {status['queue_size']}")

# 查看所有任务
tasks = get_all_tasks()
for task in tasks:
    print(f"{task['name']}: {task['status']}")
```

## 故障排除

### 1. 训练失败
- 检查数据目录结构是否正确
- 确认图片数量是否满足要求
- 查看Web界面中的训练日志

### 2. 内存不足
- 在配置文件中减小 `train_batch_size`
- 降低 `image_size` 设置
- 使用CPU训练（设置 `accelerator: cpu`）

### 3. 依赖问题
```bash
# 重新安装anomalib
pip uninstall anomalib
pip install anomalib

# 验证安装
anomalib --help
```

## 监控和日志

### Web界面功能

#### 增强版界面 (http://localhost:5001)
- **系统概览**: 队列状态和最近任务
- **模型管理**: 查看所有已训练模型，支持下载
- **任务管理**: 完整的训练任务列表
- **添加任务**: 支持权重检查和强制重训选项

- 模型文件下载
- 训练日志查看

### 日志文件
- 系统日志：`logs/training_YYYYMMDD.log`
- 训练日志：`training_results/任务ID/training.log`

## 性能优化

### GPU加速
确保安装了CUDA版本的PyTorch：
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 批处理优化
- 增加 `num_workers` 提高数据加载速度
- 调整 `train_batch_size` 平衡内存和速度
- 使用 `precision: 16` 启用混合精度训练

## 扩展功能

### 添加新模型
1. 在 `configs/model/` 添加新的配置文件
2. 在 `pcb_training_system.py` 中添加模型类型支持

### 自定义数据处理
修改 `文件监听.py` 中的数据处理逻辑

### 集成监控工具
- TensorBoard: 在配置中添加 `logger: tensorboard`
- Weights & Biases: 在配置中添加 `logger: wandb`

