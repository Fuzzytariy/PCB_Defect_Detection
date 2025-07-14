# PCB训练系统权重管理功能

## 功能概述

PCB训练系统现在支持基于产品号+元件名的智能权重管理：

1. **自动检查已有权重** - 避免重复训练相同产品
2. **统一权重存储** - 所有模型权重集中管理
3. **支持强制重训** - 可选择忽略已有权重重新训练
4. **完整信息记录** - 保存训练时间、指标等详细信息

## 权重命名规则

### 文件命名格式
```
产品号_元件名_模型类型.ckpt          # 模型权重文件
产品号_元件名_模型类型_info.json    # 模型信息文件
```

### 示例
```
trained_models/
├── 2150155000_PC1_patchcore.ckpt
├── 2150155000_PC1_patchcore_info.json
├── 2150155000_PC1_efficient_ad.ckpt
├── 2150155000_PC1_efficient_ad_info.json
├── 2040351050_BR1_patchcore.ckpt
└── 2040351050_BR1_patchcore_info.json
```

## 产品号和元件名传参

### 1. 自动传参（推荐）
通过训练目录监听器自动传参：

```python
# 从文件夹名解析产品号_元件名
product_component = "2150155000_PC1"
task_id = add_training_task(
    name=product_component,  # 作为唯一标识
    data_root=data_root,
    model_type="patchcore"
)
```

### 2. 手动传参
```python
from pcb_training_system import add_training_task

task_id = add_training_task(
    name="2150155000_PC1",  # 产品号_元件名
    data_root="/path/to/data/2150155000_PC1",
    model_type="patchcore"
)
```

## API接口

### 检查模型是否存在
```python
from pcb_training_system import check_model_exists

exists = check_model_exists("2150155000_PC1", "patchcore")
```

### 获取模型信息
```python
from pcb_training_system import get_model_info

# 获取特定模型信息
info = get_model_info("2150155000_PC1", "patchcore")

# 获取产品的所有模型
all_models = get_model_info("2150155000_PC1")
```

### 强制重新训练
```python
task_id = add_training_task(
    name="2150155000_PC1",
    data_root="/path/to/data",
    model_type="patchcore",
    force_retrain=True  # 忽略已有权重
)
```

## Web界面功能

### 增强版界面 (http://localhost:5001)

1. **模型管理页面** - 查看所有已训练模型
2. **权重检查功能** - 检查指定产品的模型是否存在
3. **强制重训选项** - 支持忽略已有权重重新训练
4. **模型下载功能** - 直接下载训练好的权重文件

## 使用场景

### 正常训练流程
1. 系统检测到新的产品数据
2. 自动检查是否已有该产品的权重
3. 如果没有权重，开始训练
4. 如果已有权重，跳过训练

### 强制重训场景
1. 通过Web界面手动添加任务
2. 勾选"强制重新训练"选项
3. 系统忽略已有权重，开始新训练

## 优势特点

1. **避免重复训练** - 节省计算资源
2. **统一权重管理** - 集中存储，便于管理
3. **灵活训练控制** - 支持强制重训
4. **完整信息追踪** - 记录详细的模型信息

