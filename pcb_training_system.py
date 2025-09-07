"""
PCB缺陷检测训练系统 - 基于Anomalib
提供完整的训练流程管理和结果记录功能
"""

import json
import logging
import os
import queue
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml


class TaskStatus(Enum):
    """训练任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingTask:
    """训练任务数据类"""
    task_id: str
    name: str
    data_root: str
    model_config: str
    data_config: str
    output_dir: str
    created_at: datetime
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    model_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 处理datetime对象
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, TaskStatus):
                data[key] = value.value
        return data


class PCBTrainingSystem:
    """PCB训练系统主类"""

    def __init__(self, base_dir: str = None):
        """
        初始化训练系统

        Args:
            base_dir: 系统基础目录，默认为当前脚本目录
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.configs_dir = self.base_dir / "configs"
        self.results_dir = self.base_dir / "training_results"
        self.logs_dir = self.base_dir / "logs"
        self.models_dir = self.base_dir / "trained_models"  # 存放训练好的模型权重

        # 创建必要的目录
        self.results_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

        # 任务管理
        self.tasks: Dict[str, TrainingTask] = {}
        self.task_queue = queue.Queue()
        self.current_task: Optional[TrainingTask] = None
        self.worker_thread = None
        self.is_running = False
        self._task_counter = 0
        self._lock = threading.Lock()

        # 配置日志
        self._setup_logging()

        # 加载历史任务
        self._load_tasks()

        # 启动工作线程
        self.start_worker()

    def _setup_logging(self):
        """配置日志系统"""
        log_file = self.logs_dir / f"training_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("PCB训练系统初始化完成")

    def _generate_task_id(self) -> str:
        """生成唯一任务ID"""
        with self._lock:
            self._task_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"pcb_task_{timestamp}_{self._task_counter:04d}"

    def _deep_update(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """递归更新字典"""
        for k, v in u.items():
            if isinstance(v, dict) and isinstance(d.get(k), dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d

    def add_training_task(
        self,
        name: str,
        data_root: str,
        model_config_name: str = "supersimple_pcb.yaml",
        force_retrain: bool = False,
        model_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加训练任务

        Args:
            name: 任务名称（通常是产品号_元件名）
            data_root: 数据根目录
            model_config_name: 模型配置文件名称（位于 configs/model 下）
            force_retrain: 是否强制重新训练，忽略已有权重
            model_params: 额外的模型参数，用于覆盖配置文件

        Returns:
            任务ID
        """
        # 检查数据目录是否存在且结构正确
        if not self._validate_data_structure(data_root):
            raise ValueError(f"数据目录结构不正确: {data_root}")

        model_key = Path(model_config_name).stem

        # 检查是否已有训练好的权重文件
        if not force_retrain and self._check_existing_model(name, model_key):
            self.logger.info(f"产品 {name} 的 {model_key} 模型已存在，跳过训练")
            return f"existing_model_{name}_{model_key}"

        # 检查是否已存在相同任务
        existing_task_id = self._find_existing_task(name, data_root)
        if existing_task_id:
            existing_task = self.tasks[existing_task_id]
            if existing_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.logger.info(f"任务 {name} 已存在且正在处理中，跳过重复添加")
                return existing_task_id

        # 创建任务
        task_id = self._generate_task_id()
        output_dir = str(self.results_dir / task_id)

        # 选择配置文件
        model_config = f"configs/model/{model_config_name}"
        data_config = "configs/data/pcb_folder.yaml"

        task = TrainingTask(
            task_id=task_id,
            name=name,
            data_root=data_root,
            model_config=model_config,
            data_config=data_config,
            output_dir=output_dir,
            created_at=datetime.now(),
            model_params=model_params
        )

        self.tasks[task_id] = task
        self.task_queue.put(task_id)
        self._save_tasks()

        self.logger.info(f"添加训练任务: {task_id} - {name}")
        return task_id

    def _validate_data_structure(self, data_root: str) -> bool:
        """验证数据目录结构"""
        data_path = Path(data_root)
        required_dirs = [
            data_path / "train" / "OK",
            data_path / "test" / "OK",
            data_path / "test" / "NG"
        ]

        for dir_path in required_dirs:
            if not dir_path.exists() or not dir_path.is_dir():
                self.logger.error(f"缺少必要目录: {dir_path}")
                return False

            # 检查是否有图片文件
            image_files = list(dir_path.glob("*.jpg")) + list(dir_path.glob("*.png"))
            if not image_files:
                self.logger.error(f"目录中没有图片文件: {dir_path}")
                return False

        return True

    def _find_existing_task(self, name: str, data_root: str) -> Optional[str]:
        """查找是否存在相同任务"""
        for task_id, task in self.tasks.items():
            if task.name == name and task.data_root == data_root:
                return task_id
        return None

    def _check_existing_model(self, name: str, model_key: str) -> bool:
        """检查是否已存在训练好的模型权重"""
        model_file = self.models_dir / f"{name}_{model_key}.ckpt"
        model_info_file = self.models_dir / f"{name}_{model_key}_info.json"

        # 检查模型文件和信息文件是否都存在
        if model_file.exists() and model_info_file.exists():
            try:
                # 验证模型信息文件的完整性
                with open(model_info_file, 'r', encoding='utf-8') as f:
                    model_info = json.load(f)

                # 检查必要的字段
                required_fields = ['name', 'model_type', 'created_at', 'model_path']
                if all(field in model_info for field in required_fields):
                    self.logger.info(f"找到已有模型: {model_file}")
                    return True
            except Exception as e:
                self.logger.warning(f"模型信息文件损坏: {e}")

        return False

    def _save_trained_model(self, task: TrainingTask):
        """保存训练好的模型到统一的模型目录"""
        if not task.model_path or not Path(task.model_path).exists():
            self.logger.warning(f"任务 {task.name} 没有找到有效的模型文件")
            return

        model_key = Path(task.model_config).stem

        # 目标文件路径
        target_model_file = self.models_dir / f"{task.name}_{model_key}.ckpt"
        target_info_file = self.models_dir / f"{task.name}_{model_key}_info.json"

        try:
            # 复制模型文件
            import shutil
            shutil.copy2(task.model_path, target_model_file)

            # 创建模型信息文件
            model_info = {
                'name': task.name,
                'model_type': model_key,
                'task_id': task.task_id,
                'created_at': task.completed_at.isoformat() if task.completed_at else datetime.now().isoformat(),
                'model_path': str(target_model_file),
                'data_root': task.data_root,
                'metrics': task.metrics,
                'config_files': {
                    'model_config': task.model_config,
                    'data_config': task.data_config
                }
            }

            with open(target_info_file, 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)

            self.logger.info(f"模型已保存: {target_model_file}")

        except Exception as e:
            self.logger.error(f"保存模型失败: {e}")

    def get_model_info(self, name: str, model_key: str = None) -> Optional[Dict[str, Any]]:
        """获取指定产品的模型信息"""
        if model_key:
            info_file = self.models_dir / f"{name}_{model_key}_info.json"
            if info_file.exists():
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    self.logger.error(f"读取模型信息失败: {e}")
        else:
            models = {}
            pattern = f"{name}_*_info.json"
            for info_file in self.models_dir.glob(pattern):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        model_type = data.get('model_type', info_file.stem)
                        models[model_type] = data
                except Exception as e:
                    self.logger.error(f"读取模型信息失败: {e}")
            return models if models else None

        return None

    def list_model_configs(self) -> List[str]:
        """列出可用的模型配置文件"""
        model_dir = self.configs_dir / "model"
        return [f.name for f in model_dir.glob("*.yaml")]

    def load_model_config(self, config_name: str) -> Dict[str, Any]:
        """加载指定的模型配置文件"""
        path = self.configs_dir / "model" / config_name
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def list_all_models(self) -> List[Dict[str, Any]]:
        """列出所有已训练的模型"""
        models = []
        for info_file in self.models_dir.glob("*_info.json"):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    model_info = json.load(f)
                    models.append(model_info)
            except Exception as e:
                self.logger.error(f"读取模型信息失败 {info_file}: {e}")

        # 按创建时间排序
        models.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return models

    def start_worker(self):
        """启动工作线程"""
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("训练工作线程已启动")

    def stop_worker(self):
        """停止工作线程"""
        self.is_running = False
        self.task_queue.put(None)  # 停止信号
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        self.logger.info("训练工作线程已停止")

    def _worker_loop(self):
        """工作线程主循环"""
        while self.is_running:
            try:
                task_id = self.task_queue.get(timeout=1)
                if task_id is None:  # 停止信号
                    break

                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue

                self._execute_training_task(task)

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"工作线程异常: {e}")

    def _execute_training_task(self, task: TrainingTask):
        """执行训练任务"""
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._save_tasks()

        self.logger.info(f"开始执行训练任务: {task.task_id} - {task.name}")

        try:
            # 创建输出目录
            os.makedirs(task.output_dir, exist_ok=True)

            # 准备配置文件
            self._prepare_configs(task)

            # 执行训练
            self._run_anomalib_training(task)

            # 解析训练结果
            self._parse_training_results(task)

            # 保存训练好的模型到统一目录
            self._save_trained_model(task)

            # 训练成功
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.logger.info(f"训练任务完成: {task.task_id} - {task.name}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self.logger.error(f"训练任务失败: {task.task_id} - {task.name}, 错误: {e}")

        finally:
            self.current_task = None
            self._save_tasks()

    def _prepare_configs(self, task: TrainingTask):
        """准备训练配置文件"""
        # 读取数据配置模板
        data_config_path = self.base_dir / task.data_config
        with open(data_config_path, 'r', encoding='utf-8') as f:
            data_config = yaml.safe_load(f)

        # 设置数据根目录
        data_config['init_args']['root'] = task.data_root
        data_config['init_args']['name'] = task.name

        # 保存临时配置文件
        temp_data_config = Path(task.output_dir) / "data_config.yaml"
        with open(temp_data_config, 'w', encoding='utf-8') as f:
            yaml.dump(data_config, f, default_flow_style=False, allow_unicode=True)

        # 复制模型配置文件
        model_config_path = self.base_dir / task.model_config
        temp_model_config = Path(task.output_dir) / "model_config.yaml"

        with open(model_config_path, 'r', encoding='utf-8') as f:
            model_config = yaml.safe_load(f)

        # 应用额外的模型参数
        if task.model_params:
            self._deep_update(model_config, task.model_params)

        # 设置输出目录
        if 'trainer' not in model_config:
            model_config['trainer'] = {}
        model_config['trainer']['default_root_dir'] = task.output_dir

        with open(temp_model_config, 'w', encoding='utf-8') as f:
            yaml.dump(model_config, f, default_flow_style=False, allow_unicode=True)

        # 更新任务配置路径
        task.data_config = str(temp_data_config)
        task.model_config = str(temp_model_config)

    def _run_anomalib_training(self, task: TrainingTask):
        """运行anomalib训练"""
        self.logger.info(f"开始Anomalib训练: {task.name}")

        try:
            # 导入anomalib模块
            from anomalib.engine import Engine
            from anomalib.data import Folder
            import yaml
            from pathlib import Path

            # 读取配置文件
            with open(task.model_config, 'r', encoding='utf-8') as f:
                model_config = yaml.safe_load(f)

            with open(task.data_config, 'r', encoding='utf-8') as f:
                data_config = yaml.safe_load(f)

            self.logger.info(f"配置加载完成，开始真实训练...")

            # 创建数据模块
            datamodule = Folder(
                root=data_config['init_args']['root'],
                normal_dir=data_config['init_args']['normal_dir'],
                abnormal_dir=data_config['init_args']['abnormal_dir'],
                normal_test_dir=data_config['init_args']['normal_test_dir'],
                mask_dir=data_config['init_args'].get('mask_dir'),
                extensions=data_config['init_args']['extensions'],
                image_size=data_config['init_args']['image_size'],
                train_batch_size=data_config['init_args']['train_batch_size'],
                eval_batch_size=data_config['init_args']['eval_batch_size'],
                num_workers=data_config['init_args']['num_workers'],
                task=data_config['init_args']['task'],
                test_split_mode=data_config['init_args']['test_split_mode'],
                test_split_ratio=data_config['init_args']['test_split_ratio'],
                val_split_mode=data_config['init_args']['val_split_mode'],
                val_split_ratio=data_config['init_args']['val_split_ratio'],
                seed=data_config['init_args']['seed']
            )

            # 根据配置创建模型
            model_class_path = model_config['model']['class_path']
            model_init_args = model_config['model']['init_args']

            if 'IncrementalSuperSimpleNet' in model_class_path:
                from incremental_supersimple import IncrementalSuperSimpleNet
                # 加载旧权重以进行增量学习
                old_weights = {}
                model_key = Path(task.model_config).stem
                old_model_file = self.models_dir / f"{task.name}_{model_key}.ckpt"
                if old_model_file.exists():
                    import torch
                    state = torch.load(old_model_file, map_location='cpu')
                    state_dict = state.get('state_dict', state)
                    old_weights = {k: v for k, v in state_dict.items()}
                model_init_args['old_weights'] = old_weights
                model = IncrementalSuperSimpleNet(**model_init_args)
            else:
                raise ValueError(f"不支持的模型类型: {model_class_path}")

            # 创建训练引擎
            trainer_config = model_config.get('trainer', {})

            # 处理callbacks配置
            callbacks = []
            if 'callbacks' in trainer_config:
                for callback_config in trainer_config['callbacks']:
                    if isinstance(callback_config, dict) and 'class_path' in callback_config:
                        # 动态导入callback类
                        class_path = callback_config['class_path']
                        init_args = callback_config.get('init_args', {})

                        # 导入callback类
                        module_path, class_name = class_path.rsplit('.', 1)
                        module = __import__(module_path, fromlist=[class_name])
                        callback_class = getattr(module, class_name)

                        # 创建callback实例
                        callback = callback_class(**init_args)
                        callbacks.append(callback)

            engine = Engine(
                max_epochs=trainer_config.get('max_epochs', 1),
                accelerator=trainer_config.get('accelerator', 'auto'),
                devices=trainer_config.get('devices', 1),
                precision=trainer_config.get('precision', 32),
                enable_checkpointing=trainer_config.get('enable_checkpointing', True),
                enable_progress_bar=trainer_config.get('enable_progress_bar', True),
                log_every_n_steps=trainer_config.get('log_every_n_steps', 10),
                default_root_dir=task.output_dir,
                callbacks=callbacks
            )

            self.logger.info(f"开始训练模型: {model.__class__.__name__}")
            self.logger.info(f"数据根目录: {data_config['init_args']['root']}")
            self.logger.info(f"输出目录: {task.output_dir}")

            # 执行训练
            engine.fit(datamodule=datamodule, model=model)

            self.logger.info(f"训练完成: {task.name}")

            # 查找生成的模型文件
            output_path = Path(task.output_dir)

            # 查找checkpoint文件
            ckpt_files = list(output_path.rglob("*.ckpt"))
            if ckpt_files:
                # 选择最新的checkpoint文件
                latest_ckpt = max(ckpt_files, key=lambda x: x.stat().st_mtime)
                task.model_path = str(latest_ckpt)
                self.logger.info(f"找到模型文件: {task.model_path}")
            else:
                self.logger.warning("未找到checkpoint文件")

            # 尝试获取训练指标
            try:
                # 查找指标文件
                metrics_files = list(output_path.rglob("*metrics*.csv"))
                if not metrics_files:
                    metrics_files = list(output_path.rglob("*metrics*.json"))

                if metrics_files:
                    self._parse_training_results_from_file(task, metrics_files[0])
                else:
                    self.logger.warning("未找到指标文件，使用默认指标")
                    # 设置默认指标（如果无法获取真实指标）
                    task.metrics = {
                        "training_completed": True,
                        "model_type": model.__class__.__name__
                    }
            except Exception as e:
                self.logger.warning(f"解析训练指标失败: {e}")
                task.metrics = {
                    "training_completed": True,
                    "model_type": model.__class__.__name__
                }

            self.logger.info(f"训练任务完成: {task.name}")

        except ImportError as e:
            self.logger.error(f"Anomalib导入失败，请确保已正确安装anomalib: {e}")
            raise RuntimeError(f"Anomalib导入失败: {e}")
        except Exception as e:
            self.logger.error(f"Anomalib训练失败: {e}")
            raise RuntimeError(f"Anomalib训练失败: {e}")

    def _parse_training_results_from_file(self, task: TrainingTask, metrics_file: Path):
        """从文件解析训练结果"""
        try:
            if metrics_file.suffix == '.json':
                import json
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)

                task.metrics = {}
                for key, value in metrics_data.items():
                    if isinstance(value, (int, float)):
                        task.metrics[key] = float(value)

            elif metrics_file.suffix == '.csv':
                import pandas as pd
                df = pd.read_csv(metrics_file)

                if not df.empty:
                    last_row = df.iloc[-1]
                    task.metrics = {}
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]) and not pd.isna(last_row[col]):
                            task.metrics[col] = float(last_row[col])

            self.logger.info(f"成功解析训练指标: {task.metrics}")

        except Exception as e:
            self.logger.warning(f"解析指标文件失败: {e}")
            task.metrics = {
                "training_completed": True,
                "parse_error": str(e)
            }

    def _parse_training_results(self, task: TrainingTask):
        """解析训练结果"""
        # 查找模型文件
        output_path = Path(task.output_dir)

        # 查找权重文件
        weight_files = list(output_path.rglob("*.ckpt"))
        if weight_files:
            task.model_path = str(weight_files[0])

        # 查找并解析指标文件
        metrics_files = list(output_path.rglob("*metrics*.json"))
        if not metrics_files:
            # 尝试查找CSV文件
            metrics_files = list(output_path.rglob("*metrics*.csv"))

        if metrics_files:
            self._parse_training_results_from_file(task, metrics_files[0])

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详细信息"""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        pending_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]

        return {
            "queue_size": len(pending_tasks),
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "pending_tasks": [task.to_dict() for task in pending_tasks]
        }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        return [task.to_dict() for task in self.tasks.values()]

    def cancel_task(self, task_id: str) -> bool:
        """取消等待中的任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self._save_tasks()
            self.logger.info(f"任务 {task_id} 已取消")
            return True
        else:
            self.logger.warning(f"无法取消任务 {task_id}，当前状态: {task.status.value}")
            return False

    def _save_tasks(self):
        """保存任务信息到文件"""
        tasks_file = self.results_dir / "tasks.json"
        tasks_data = [task.to_dict() for task in self.tasks.values()]

        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)

    def _load_tasks(self):
        """从文件加载任务信息"""
        tasks_file = self.results_dir / "tasks.json"
        if not tasks_file.exists():
            return

        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)

            for task_data in tasks_data:
                # 重建任务对象
                task = TrainingTask(
                    task_id=task_data["task_id"],
                    name=task_data["name"],
                    data_root=task_data["data_root"],
                    model_config=task_data["model_config"],
                    data_config=task_data["data_config"],
                    output_dir=task_data["output_dir"],
                    created_at=datetime.fromisoformat(task_data["created_at"]),
                    status=TaskStatus(task_data["status"]),
                    started_at=datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None,
                    error_message=task_data.get("error_message"),
                    metrics=task_data.get("metrics"),
                    model_path=task_data.get("model_path"),
                    model_params=task_data.get("model_params")
                )
                self.tasks[task.task_id] = task

                # 更新任务计数器
                if task.task_id.startswith("pcb_task_"):
                    try:
                        counter = int(task.task_id.split("_")[-1])
                        self._task_counter = max(self._task_counter, counter)
                    except:
                        pass

        except Exception as e:
            self.logger.error(f"加载任务文件失败: {e}")


# 全局训练系统实例
training_system = PCBTrainingSystem()


def add_training_task(
    name: str,
    data_root: str,
    model_config_name: str = "supersimple_pcb.yaml",
    force_retrain: bool = False,
    model_params: Optional[Dict[str, Any]] = None
) -> str:
    """便捷函数：添加训练任务"""
    return training_system.add_training_task(name, data_root, model_config_name, force_retrain, model_params)


def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取任务信息"""
    return training_system.get_task_info(task_id)


def get_queue_status() -> Dict[str, Any]:
    """便捷函数：获取队列状态"""
    return training_system.get_queue_status()


def get_all_tasks() -> List[Dict[str, Any]]:
    """便捷函数：获取所有任务"""
    return training_system.get_all_tasks()


def get_model_info(name: str, model_key: str = None) -> Optional[Dict[str, Any]]:
    """便捷函数：获取模型信息"""
    return training_system.get_model_info(name, model_key)


def list_all_models() -> List[Dict[str, Any]]:
    """便捷函数：列出所有模型"""
    return training_system.list_all_models()


def check_model_exists(name: str, model_key: str) -> bool:
    """便捷函数：检查模型是否存在"""
    return training_system._check_existing_model(name, model_key)


def list_model_configs() -> List[str]:
    """列出可用的模型配置文件"""
    return training_system.list_model_configs()


def load_model_config(config_name: str) -> Dict[str, Any]:
    """加载指定模型配置文件"""
    return training_system.load_model_config(config_name)


if __name__ == "__main__":
    # 测试代码
    import time

    # 创建测试数据目录结构（仅用于演示）
    test_data_root = "test_data/sample_pcb"

    print("PCB训练系统测试")
    print("=" * 50)

    # 显示队列状态
    status = get_queue_status()
    print(f"当前队列状态: {status}")

    # 如果有测试数据，可以添加任务
    # task_id = add_training_task("test_pcb_001", test_data_root)
    # print(f"添加测试任务: {task_id}")

    # 等待一段时间
    time.sleep(2)

    # 显示所有任务
    all_tasks = get_all_tasks()
    print(f"所有任务数量: {len(all_tasks)}")
    for task in all_tasks:
        print(f"  - {task['task_id']}: {task['name']} ({task['status']})")

