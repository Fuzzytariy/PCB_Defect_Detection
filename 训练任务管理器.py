import os
import time
import threading
import queue
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json

from 算法端 import AlgoSystem


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TrainingTask:
    """训练任务数据类"""
    task_id: str
    name: str
    root: str
    backbone: str
    layers: list
    coreset_sampling_ratio: float
    num_neighbors: int
    created_at: datetime
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TrainingTaskManager:
    """训练任务管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.task_queue = queue.Queue()
        self.tasks: Dict[str, TrainingTask] = {}
        self.current_task: Optional[TrainingTask] = None
        self.worker_thread = None
        self.is_running = False
        self._task_counter = 0
        self._counter_lock = threading.Lock()
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 启动工作线程
        self.start_worker()
    
    def _generate_task_id(self) -> str:
        """生成唯一的任务ID"""
        with self._counter_lock:
            self._task_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"task_{timestamp}_{self._task_counter:04d}"
    
    def add_training_task(
        self,
        name: str,
        root: str,
        backbone: str = "resnet18",
        layers: list = None,
        coreset_sampling_ratio: float = 0.1,
        num_neighbors: int = 9
    ) -> str:
        """
        添加训练任务到队列
        
        Args:
            name: 数据集名称
            root: 数据根目录
            backbone: 骨干网络
            layers: 特征层
            coreset_sampling_ratio: 核心集采样比例
            num_neighbors: 邻居数量
            
        Returns:
            任务ID
        """
        if layers is None:
            layers = ['layer1', 'layer2', 'layer3']
        
        # 检查是否已存在相同的任务（基于name和root）
        existing_task_id = self._find_existing_task(name, root)
        if existing_task_id:
            existing_task = self.tasks[existing_task_id]
            if existing_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.logger.info(f"任务 {name} 已存在且正在处理中，跳过重复添加")
                return existing_task_id
        
        task_id = self._generate_task_id()
        task = TrainingTask(
            task_id=task_id,
            name=name,
            root=root,
            backbone=backbone,
            layers=layers,
            coreset_sampling_ratio=coreset_sampling_ratio,
            num_neighbors=num_neighbors,
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        self.task_queue.put(task_id)
        
        self.logger.info(f"添加训练任务: {task_id} - {name}")
        return task_id
    
    def _find_existing_task(self, name: str, root: str) -> Optional[str]:
        """查找是否存在相同的任务"""
        for task_id, task in self.tasks.items():
            if task.name == name and task.root == root:
                return task_id
        return None
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详细信息"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "root": task.root,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        pending_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
        running_task = self.current_task
        
        return {
            "queue_size": len(pending_tasks),
            "current_task": {
                "task_id": running_task.task_id,
                "name": running_task.name,
                "started_at": running_task.started_at.isoformat()
            } if running_task else None,
            "pending_tasks": [
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "created_at": task.created_at.isoformat()
                }
                for task in pending_tasks
            ]
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务（仅能取消等待中的任务）"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self.logger.info(f"任务 {task_id} 已取消")
            return True
        else:
            self.logger.warning(f"无法取消任务 {task_id}，当前状态: {task.status.value}")
            return False
    
    def start_worker(self):
        """启动工作线程"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("训练任务工作线程已启动")
    
    def stop_worker(self):
        """停止工作线程"""
        self.is_running = False
        # 添加一个停止信号到队列
        self.task_queue.put(None)
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.logger.info("训练任务工作线程已停止")
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.is_running:
            try:
                # 从队列获取任务ID，超时时间1秒
                task_id = self.task_queue.get(timeout=1)
                
                # 检查停止信号
                if task_id is None:
                    break
                
                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # 执行训练任务
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
        
        self.logger.info(f"开始执行训练任务: {task.task_id} - {task.name}")
        
        try:
            # 检查数据目录是否存在
            if not os.path.exists(task.root):
                raise FileNotFoundError(f"数据目录不存在: {task.root}")
            
            # 创建算法系统实例
            system = AlgoSystem(
                name=task.name,
                root=task.root,
                normalization_method="min_max",
                image_metrics=["F1Score", "AUROC"],
            )
            
            # 执行训练
            system.train(
                backbone=task.backbone,
                layers=task.layers,
                coreset_sampling_ratio=task.coreset_sampling_ratio,
                num_neighbors=task.num_neighbors,
            )
            
            # 训练成功
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.logger.info(f"训练任务完成: {task.task_id} - {task.name}")
            
        except Exception as e:
            # 训练失败
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self.logger.error(f"训练任务失败: {task.task_id} - {task.name}, 错误: {e}")
        
        finally:
            self.current_task = None
    
    def save_tasks_to_file(self, filepath: str):
        """保存任务信息到文件"""
        tasks_data = []
        for task in self.tasks.values():
            task_data = {
                "task_id": task.task_id,
                "name": task.name,
                "root": task.root,
                "backbone": task.backbone,
                "layers": task.layers,
                "coreset_sampling_ratio": task.coreset_sampling_ratio,
                "num_neighbors": task.num_neighbors,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message
            }
            tasks_data.append(task_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
    
    def load_tasks_from_file(self, filepath: str):
        """从文件加载任务信息"""
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            for task_data in tasks_data:
                task = TrainingTask(
                    task_id=task_data["task_id"],
                    name=task_data["name"],
                    root=task_data["root"],
                    backbone=task_data["backbone"],
                    layers=task_data["layers"],
                    coreset_sampling_ratio=task_data["coreset_sampling_ratio"],
                    num_neighbors=task_data["num_neighbors"],
                    created_at=datetime.fromisoformat(task_data["created_at"]),
                    status=TaskStatus(task_data["status"]),
                    error_message=task_data.get("error_message"),
                    started_at=datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None
                )
                self.tasks[task.task_id] = task
                
        except Exception as e:
            self.logger.error(f"加载任务文件失败: {e}")


# 全局任务管理器实例
task_manager = TrainingTaskManager()


def add_training_task(name: str, root: str, **kwargs) -> str:
    """便捷函数：添加训练任务"""
    return task_manager.add_training_task(name, root, **kwargs)


def get_task_status(task_id: str) -> Optional[TaskStatus]:
    """便捷函数：获取任务状态"""
    return task_manager.get_task_status(task_id)


def get_queue_status() -> Dict[str, Any]:
    """便捷函数：获取队列状态"""
    return task_manager.get_queue_status()


if __name__ == "__main__":
    # 测试代码
    import time
    
    # 添加几个测试任务
    task1 = add_training_task("test1", "/path/to/data1")
    task2 = add_training_task("test2", "/path/to/data2")
    task3 = add_training_task("test3", "/path/to/data3")
    
    print("队列状态:", get_queue_status())
    
    # 等待一段时间观察任务执行
    time.sleep(5)
    
    print("任务1状态:", get_task_status(task1))
    print("任务2状态:", get_task_status(task2))
    print("任务3状态:", get_task_status(task3))