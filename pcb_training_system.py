"""PCB缺陷检测训练系统 - 基于YOLOv8二分类增量学习"""

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

import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from ultralytics import YOLO


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingTask:
    task_id: str
    name: str
    data_root: str
    output_dir: str
    created_at: datetime
    model_type: str = "yolov8"
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, TaskStatus):
                data[key] = value.value
        return data


class PCBTrainingSystem:
    def __init__(self, base_dir: str = None, beta: float = 0.01):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.results_dir = self.base_dir / "training_results"
        self.logs_dir = self.base_dir / "logs"
        self.models_dir = self.base_dir / "trained_models"
        for d in [self.results_dir, self.logs_dir, self.models_dir]:
            d.mkdir(exist_ok=True)

        self.tasks: Dict[str, TrainingTask] = {}
        self.task_queue = queue.Queue()
        self.current_task: Optional[TrainingTask] = None
        self.worker_thread = None
        self.is_running = False
        self._task_counter = 0
        self._lock = threading.Lock()
        self.beta = beta

        self._setup_logging()
        self._load_tasks()
        self.start_worker()

    def _setup_logging(self):
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
        with self._lock:
            self._task_counter += 1
            return f"pcb_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._task_counter:04d}"

    def _validate_data_structure(self, data_root: str) -> bool:
        root = Path(data_root)
        required = [root / "train" / "OK", root / "test" / "OK", root / "test" / "NG"]
        for p in required:
            if not p.exists() or not any(p.glob("*.jpg")):
                self.logger.error(f"缺少必要目录或图片: {p}")
                return False
        return True

    def _find_existing_task(self, name: str, data_root: str) -> Optional[str]:
        for tid, t in self.tasks.items():
            if t.name == name and t.data_root == data_root:
                return tid
        return None

    def _check_existing_model(self, name: str, model_type: str) -> bool:
        model_file = self.models_dir / f"{name}_{model_type}.pt"
        info_file = self.models_dir / f"{name}_{model_type}_info.json"
        return model_file.exists() and info_file.exists()

    def add_training_task(self, name: str, data_root: str, model_type: str = "yolov8", force_retrain: bool = False) -> str:
        if not self._validate_data_structure(data_root):
            raise ValueError(f"数据目录结构不正确: {data_root}")
        if not force_retrain and self._check_existing_model(name, model_type):
            self.logger.info(f"产品 {name} 的 {model_type} 模型已存在，跳过训练")
            return f"existing_model_{name}_{model_type}"
        existing = self._find_existing_task(name, data_root)
        if existing:
            task = self.tasks[existing]
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.logger.info(f"任务 {name} 已存在且正在处理中，跳过重复添加")
                return existing
        task_id = self._generate_task_id()
        output_dir = str(self.results_dir / task_id)
        task = TrainingTask(task_id=task_id, name=name, data_root=data_root, output_dir=output_dir, created_at=datetime.now(), model_type=model_type)
        self.tasks[task_id] = task
        self.task_queue.put(task_id)
        self._save_tasks()
        self.logger.info(f"添加训练任务: {task_id} - {name}")
        return task_id

    def start_worker(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("训练工作线程已启动")

    def _worker_loop(self):
        while self.is_running:
            try:
                task_id = self.task_queue.get(timeout=1)
            except queue.Empty:
                continue
            if task_id is None:
                break
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                self._execute_training_task(task)

    def _execute_training_task(self, task: TrainingTask):
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._save_tasks()
        try:
            os.makedirs(task.output_dir, exist_ok=True)
            self._run_yolov8_training(task)
            self._save_trained_model(task)
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

    def _run_yolov8_training(self, task: TrainingTask):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        base_model = YOLO("yolov8n-cls.pt")
        old_model_path = self.models_dir / f"{task.name}_{task.model_type}.pt"
        if old_model_path.exists():
            base_model = YOLO(str(old_model_path))
        model = base_model.model.to(device)
        old_weights = {name: param.clone().detach().to(device) for name, param in model.named_parameters() if param.requires_grad and 'weight' in name}

        transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        train_dataset = ImageFolder(Path(task.data_root) / "train", transform=transform)
        test_dataset = ImageFolder(Path(task.data_root) / "test", transform=transform)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

        criterion = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        epochs = 5
        for _ in range(epochs):
            model.train()
            for imgs, labels in train_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(imgs)
                base_loss = criterion(outputs, labels)
                alignment_loss = 0.0
                count = 0
                for name, param in model.named_parameters():
                    if name in old_weights and param.requires_grad and 'weight' in name:
                        diff = param - old_weights[name]
                        alignment_loss += torch.norm(diff, p=2) ** 2
                        count += 1
                if count > 0:
                    alignment_loss = alignment_loss / count * self.beta
                loss = base_loss + alignment_loss
                loss.backward()
                optimizer.step()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for imgs, labels in test_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                preds = outputs.argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        accuracy = correct / total if total > 0 else 0.0

        save_path = Path(task.output_dir) / "model.pt"
        torch.save(model.cpu().state_dict(), save_path)
        task.model_path = str(save_path)
        task.metrics = {"accuracy": accuracy}

    def _save_trained_model(self, task: TrainingTask):
        if not task.model_path or not Path(task.model_path).exists():
            self.logger.warning(f"任务 {task.name} 没有找到有效的模型文件")
            return
        import shutil
        target_model_file = self.models_dir / f"{task.name}_{task.model_type}.pt"
        target_info_file = self.models_dir / f"{task.name}_{task.model_type}_info.json"
        shutil.copy2(task.model_path, target_model_file)
        model_info = {
            'name': task.name,
            'model_type': task.model_type,
            'task_id': task.task_id,
            'created_at': task.completed_at.isoformat() if task.completed_at else datetime.now().isoformat(),
            'model_path': str(target_model_file),
            'data_root': task.data_root,
            'metrics': task.metrics,
        }
        with open(target_info_file, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        self.logger.info(f"模型已保存: {target_model_file}")

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def get_queue_status(self) -> Dict[str, Any]:
        pending = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        return {
            'queue_size': len(pending),
            'current_task': self.current_task.to_dict() if self.current_task else None,
            'pending_tasks': [t.to_dict() for t in pending]
        }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values()]

    def get_model_info(self, name: str, model_type: str = "yolov8") -> Optional[Dict[str, Any]]:
        info_file = self.models_dir / f"{name}_{model_type}_info.json"
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_all_models(self) -> List[Dict[str, Any]]:
        models = []
        for info_file in self.models_dir.glob("*_info.json"):
            with open(info_file, 'r', encoding='utf-8') as f:
                models.append(json.load(f))
        models.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return models

    def _save_tasks(self):
        tasks_file = self.results_dir / "tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.tasks.values()], f, ensure_ascii=False, indent=2)

    def _load_tasks(self):
        tasks_file = self.results_dir / "tasks.json"
        if not tasks_file.exists():
            return
        with open(tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in data:
            task = TrainingTask(
                task_id=t['task_id'],
                name=t['name'],
                data_root=t['data_root'],
                output_dir=t['output_dir'],
                created_at=datetime.fromisoformat(t['created_at']),
                model_type=t.get('model_type', 'yolov8'),
                status=TaskStatus(t['status']),
                started_at=datetime.fromisoformat(t['started_at']) if t.get('started_at') else None,
                completed_at=datetime.fromisoformat(t['completed_at']) if t.get('completed_at') else None,
                error_message=t.get('error_message'),
                metrics=t.get('metrics'),
                model_path=t.get('model_path')
            )
            self.tasks[task.task_id] = task
            if task.task_id.startswith('pcb_task_'):
                try:
                    counter = int(task.task_id.split('_')[-1])
                    self._task_counter = max(self._task_counter, counter)
                except Exception:
                    pass


# 全局训练系统实例
training_system = PCBTrainingSystem()


def add_training_task(name: str, data_root: str, model_type: str = "yolov8", force_retrain: bool = False) -> str:
    return training_system.add_training_task(name, data_root, model_type, force_retrain)


def get_task_info(task_id: str) -> Optional[Dict[str, Any]]:
    return training_system.get_task_info(task_id)


def get_queue_status() -> Dict[str, Any]:
    return training_system.get_queue_status()


def get_all_tasks() -> List[Dict[str, Any]]:
    return training_system.get_all_tasks()


def get_model_info(name: str, model_type: str = "yolov8") -> Optional[Dict[str, Any]]:
    return training_system.get_model_info(name, model_type)


def list_all_models() -> List[Dict[str, Any]]:
    return training_system.list_all_models()


def check_model_exists(name: str, model_type: str = "yolov8") -> bool:
    return training_system._check_existing_model(name, model_type)
