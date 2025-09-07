# PCB缺陷检测训练系统

基于Anomalib的完整PCB缺陷检测训练系统，提供从数据监听到模型训练的全自动化流程。

## 系统架构

```
PCB文件监听 → 数据整理 → 训练目录监听 → 自动训练 → 结果记录
     ↓              ↓              ↓           ↓          ↓
  TXT标注文件    图片分类整理    数据目录监控   Anomalib训练  Web界面展示
```

## 主要功能

### 1. 自动化数据流程
- **文件监听**: 监听TXT标注文件，自动解析产品信息和检测结果
- **图片整理**: 根据标注结果自动分类整理图片到训练/测试目录
- **数据验证**: 确保数据量满足训练要求（OK≥130张，NG≥50张）

### 2. 智能训练管理
- **队列管理**: 自动排队执行训练任务，支持并发控制
- **配置管理**: 使用Anomalib配置文件，支持SuperSimpleNet模型
- **结果记录**: 自动保存训练指标、模型文件和日志

### 3. 实时监控界面
- **状态监控**: 实时查看训练队列状态和进度
- **结果展示**: 可视化训练指标和模型性能
- **模型下载**: 支持下载训练完成的模型文件

## 目录结构

```
PCB_Defect_Detection/
├── main.py                     # 主启动脚本
├── pcb_training_system.py      # 核心训练系统
├── web_interface_enhanced.py   # Web监控界面
├── 文件监听.py                 # PCB文件监听器
├── 训练目录监听.py             # 训练目录监听器
├── configs/                    # 配置文件目录
│   ├── data/
│   │   └── pcb_folder.yaml     # 数据配置
│   ├── model/
│   │   └── supersimple_pcb.yaml # SuperSimpleNet模型配置
│   └── trigger.yaml            # 训练触发阈值配置
├── txt标注/                    # TXT标注文件目录
├── 图片数据/                   # 原始图片数据目录
├── output/                     # 整理后的数据目录
├── data/                       # 训练数据目录
├── training_results/           # 训练结果目录
├── logs/                       # 系统日志目录
└── requirements.txt            # 依赖包列表
```

## 安装和配置

### 1. 环境要求
- Python 3.8+
- CUDA 11.8+ (可选，用于GPU训练)

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 安装Anomalib
```bash
pip install anomalib
```

### 4. 验证安装
```bash
anomalib --help
```

## 使用方法

### 1. 启动完整系统
```bash
python main.py
```

系统将自动启动以下组件：
 - PCB文件监听器
 - 训练目录监听器
 - 训练任务管理器
 - Web监控界面 (http://localhost:5001)

### 2. 单独使用训练系统
```python
from pcb_training_system import add_training_task

# 添加训练任务
task_id = add_training_task(
    name="产品号_元件名",
    data_root="/path/to/data",
    model_type="supersimple"
)
```

### 3. 数据目录结构要求
```
data_root/
├── train/
│   └── OK/          # 正常样本 (≥80张)
└── test/
    ├── OK/          # 正常测试样本 (≥50张)
    └── NG/          # 异常测试样本 (≥50张)
```

## 配置说明

### 1. 模型配置
- **SuperSimpleNet**: 适用于快速增量训练

### 2. 数据配置
- 图片尺寸: 256x256 (可调整)
- 批次大小: 32 (可调整)
- 数据增强: 可选配置

### 3. 训练配置
- 自动保存最佳模型
- 支持早停机制
- 自动记录训练指标

## Web界面功能

访问 http://localhost:5001 查看：

1. **队列状态**: 当前训练任务和等待队列
2. **任务列表**: 所有训练任务的状态和结果
3. **手动添加**: 支持手动添加训练任务
4. **结果下载**: 下载训练好的模型文件
5. **日志查看**: 查看详细的训练日志

## 训练结果

每个训练任务完成后会生成：
- 模型权重文件 (.ckpt)
- 训练日志文件
- 性能指标 (AUROC, F1-Score等)
- 配置文件备份

## 故障排除

### 1. 训练失败
- 检查数据目录结构是否正确
- 确认图片文件格式支持
- 查看训练日志获取详细错误信息

### 2. 内存不足
- 减小批次大小 (train_batch_size)
- 降低图片分辨率 (image_size)
- 使用CPU训练 (设置 accelerator: cpu)

### 3. 依赖问题
```bash
# 重新安装anomalib
pip uninstall anomalib
pip install anomalib

# 检查CUDA版本
python -c "import torch; print(torch.cuda.is_available())"
```

## 扩展功能

### 1. 添加新模型
1. 在 `configs/model/` 目录添加新的配置文件
2. 在 `pcb_training_system.py` 中添加模型类型支持

### 2. 自定义数据处理
修改 `文件监听.py` 中的数据处理逻辑

### 3. 集成其他监控工具
- TensorBoard: 添加 `--trainer.logger tensorboard`
- Weights & Biases: 添加 `--trainer.logger wandb`

## 许可证

本项目基于 Apache 2.0 许可证开源。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者
