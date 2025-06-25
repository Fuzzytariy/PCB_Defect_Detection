#!/usr/bin/env python3
"""
训练API客户端示例
演示如何使用训练任务管理API
"""

import requests
import json
import time
from typing import Dict, Any, Optional


class TrainingAPIClient:
    """训练API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def create_training_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """创建训练任务"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/train",
                json=config
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/queue")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务"""
        try:
            response = self.session.get(f"{self.base_url}/api/tasks")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_task_detail(self, task_id: str) -> Dict[str, Any]:
        """获取任务详情"""
        try:
            response = self.session.get(f"{self.base_url}/api/task/{task_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        try:
            response = self.session.delete(f"{self.base_url}/api/task/{task_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_config_template(self) -> Dict[str, Any]:
        """获取配置模板"""
        try:
            response = self.session.get(f"{self.base_url}/api/config/template")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            response = self.session.get(f"{self.base_url}/api/stats")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def wait_for_task_completion(self, task_id: str, timeout: int = 3600) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.get_task_detail(task_id)
            
            if "error" in result:
                return result
            
            if result.get("success") and "data" in result:
                status = result["data"].get("status")
                if status in ["completed", "failed", "cancelled"]:
                    return result
            
            time.sleep(5)  # 每5秒检查一次
        
        return {"error": "任务等待超时"}


def demo_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("🚀 训练API客户端基本使用示例")
    print("=" * 60)
    
    # 创建客户端
    client = TrainingAPIClient("http://localhost:5000")
    
    # 1. 健康检查
    print("\n1. 健康检查...")
    health = client.health_check()
    print(f"健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
    
    # 2. 获取配置模板
    print("\n2. 获取配置模板...")
    template = client.get_config_template()
    if template.get("success"):
        print("配置模板:")
        print(json.dumps(template["data"]["template"], indent=2, ensure_ascii=False))
        print("可选参数:")
        print(json.dumps(template["data"]["options"], indent=2, ensure_ascii=False))
    
    # 3. 创建训练任务
    print("\n3. 创建训练任务...")
    training_config = {
        "name": "API测试任务",
        "root": "/Users/pimengkun/PycharmProjects/PCB_Defect_Detection/data/2150155000_PC1",  # 请修改为实际路径
        "backbone": "resnet18",
        "layers": ["layer1", "layer2", "layer3"],
        "coreset_sampling_ratio": 0.1,
        "num_neighbors": 9
    }
    
    result = client.create_training_task(training_config)
    print(f"创建结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get("success"):
        task_id = result.get("task_id")
        print(f"任务ID: {task_id}")
        
        # 4. 获取队列状态
        print("\n4. 获取队列状态...")
        queue_status = client.get_queue_status()
        if queue_status.get("success"):
            print(f"队列状态: {json.dumps(queue_status['data'], indent=2, ensure_ascii=False)}")
        
        # 5. 获取任务详情
        print("\n5. 获取任务详情...")
        task_detail = client.get_task_detail(task_id)
        if task_detail.get("success"):
            print(f"任务详情: {json.dumps(task_detail['data'], indent=2, ensure_ascii=False)}")
    
    # 6. 获取所有任务
    print("\n6. 获取所有任务...")
    all_tasks = client.get_all_tasks()
    if all_tasks.get("success"):
        data = all_tasks["data"]
        print(f"总任务数: {data['total_count']}")
        for status, tasks in data["tasks_by_status"].items():
            if tasks:
                print(f"{status.upper()}: {len(tasks)}个任务")
    
    # 7. 获取统计信息
    print("\n7. 获取统计信息...")
    stats = client.get_statistics()
    if stats.get("success"):
        print(f"统计信息: {json.dumps(stats['data'], indent=2, ensure_ascii=False)}")


def demo_batch_training():
    """批量训练示例"""
    print("=" * 60)
    print("🔄 批量训练任务示例")
    print("=" * 60)
    
    client = TrainingAPIClient("http://localhost:5000")
    
    # 批量创建训练任务
    batch_configs = [
        {
            "name": "批量任务1_ResNet18",
            "root": "/path/to/data1",  # 请修改为实际路径
            "backbone": "resnet18",
            "layers": ["layer1", "layer2", "layer3"]
        },
        {
            "name": "批量任务2_ResNet34",
            "root": "/path/to/data2",  # 请修改为实际路径
            "backbone": "resnet34",
            "layers": ["layer2", "layer3"]
        },
        {
            "name": "批量任务3_ResNet50",
            "root": "/path/to/data3",  # 请修改为实际路径
            "backbone": "resnet50",
            "layers": ["layer3"]
        }
    ]
    
    task_ids = []
    
    for i, config in enumerate(batch_configs, 1):
        print(f"\n创建任务 {i}: {config['name']}")
        result = client.create_training_task(config)
        
        if result.get("success"):
            task_id = result.get("task_id")
            task_ids.append(task_id)
            print(f"✅ 任务创建成功: {task_id}")
        else:
            print(f"❌ 任务创建失败: {result.get('error')}")
    
    # 监控任务状态
    print(f"\n📊 监控 {len(task_ids)} 个任务的执行状态...")
    
    while task_ids:
        print(f"\n当前监控任务数: {len(task_ids)}")
        
        # 检查每个任务的状态
        completed_tasks = []
        for task_id in task_ids:
            detail = client.get_task_detail(task_id)
            if detail.get("success"):
                status = detail["data"]["status"]
                name = detail["data"]["name"]
                print(f"  {name}: {status}")
                
                if status in ["completed", "failed", "cancelled"]:
                    completed_tasks.append(task_id)
        
        # 移除已完成的任务
        for task_id in completed_tasks:
            task_ids.remove(task_id)
        
        if task_ids:
            time.sleep(10)  # 等待10秒后再次检查
    
    print("\n🎉 所有任务已完成!")


def demo_task_management():
    """任务管理示例"""
    print("=" * 60)
    print("🛠️ 任务管理示例")
    print("=" * 60)
    
    client = TrainingAPIClient("http://localhost:5000")
    
    # 创建一个测试任务
    config = {
        "name": "管理测试任务",
        "root": "/path/to/test/data",  # 请修改为实际路径
        "backbone": "resnet18"
    }
    
    print("1. 创建测试任务...")
    result = client.create_training_task(config)
    
    if not result.get("success"):
        print(f"❌ 创建任务失败: {result.get('error')}")
        return
    
    task_id = result.get("task_id")
    print(f"✅ 任务创建成功: {task_id}")
    
    # 等待一段时间
    print("\n2. 等待5秒...")
    time.sleep(5)
    
    # 检查任务状态
    print("\n3. 检查任务状态...")
    detail = client.get_task_detail(task_id)
    if detail.get("success"):
        status = detail["data"]["status"]
        print(f"任务状态: {status}")
        
        # 如果任务还在等待中，尝试取消
        if status == "pending":
            print("\n4. 尝试取消任务...")
            cancel_result = client.cancel_task(task_id)
            if cancel_result.get("success"):
                print("✅ 任务取消成功")
            else:
                print(f"❌ 任务取消失败: {cancel_result.get('error')}")
        else:
            print(f"任务状态为 {status}，无法取消")


def interactive_demo():
    """交互式演示"""
    print("=" * 60)
    print("🎮 交互式API演示")
    print("=" * 60)
    
    client = TrainingAPIClient("http://localhost:5000")
    
    while True:
        print("\n请选择操作:")
        print("1. 健康检查")
        print("2. 获取队列状态")
        print("3. 获取所有任务")
        print("4. 创建训练任务")
        print("5. 获取任务详情")
        print("6. 取消任务")
        print("7. 获取统计信息")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-7): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            result = client.health_check()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "2":
            result = client.get_queue_status()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "3":
            result = client.get_all_tasks()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "4":
            name = input("任务名称: ")
            root = input("数据路径: ")
            backbone = input("骨干网络 (默认resnet18): ") or "resnet18"
            
            config = {
                "name": name,
                "root": root,
                "backbone": backbone
            }
            
            result = client.create_training_task(config)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "5":
            task_id = input("任务ID: ")
            result = client.get_task_detail(task_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "6":
            task_id = input("任务ID: ")
            result = client.cancel_task(task_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == "7":
            result = client.get_statistics()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("❌ 无效选择")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="训练API客户端示例")
    parser.add_argument("--url", default="http://localhost:5000", help="API服务地址")
    parser.add_argument("--demo", choices=["basic", "batch", "management", "interactive"], 
                       default="basic", help="演示类型")
    
    args = parser.parse_args()
    
    # 更新客户端URL
    global client
    
    if args.demo == "basic":
        demo_basic_usage()
    elif args.demo == "batch":
        demo_batch_training()
    elif args.demo == "management":
        demo_task_management()
    elif args.demo == "interactive":
        interactive_demo()


if __name__ == "__main__":
    main()