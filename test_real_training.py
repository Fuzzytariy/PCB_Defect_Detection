#!/usr/bin/env python3
"""
测试真实的anomalib训练功能
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from pcb_training_system import add_training_task, get_queue_status, get_task_info


def test_real_training():
    """测试真实训练功能"""
    print("=" * 60)
    print("测试真实Anomalib训练功能")
    print("=" * 60)

    # 检查是否有可用的测试数据
    test_data_dirs = [
        "data/2150155000_CU",
        "data/2040351050_BR1",
        "data/2150155000_PC1",
        "data/2150155000_主板组件"
    ]

    available_data = []
    for data_dir in test_data_dirs:
        if Path(data_dir).exists():
            # 检查数据结构
            required_dirs = [
                Path(data_dir) / "train" / "OK",
                Path(data_dir) / "test" / "OK",
                Path(data_dir) / "test" / "NG"
            ]

            if all(d.exists() and list(d.glob("*.jpg")) + list(d.glob("*.png")) for d in required_dirs):
                available_data.append(data_dir)
                print(f"✓ 找到可用数据: {data_dir}")
            else:
                print(f"✗ 数据结构不完整: {data_dir}")
        else:
            print(f"✗ 数据目录不存在: {data_dir}")

    if not available_data:
        print("\n没有找到可用的测试数据，请确保数据目录结构正确:")
        print("data/产品名/")
        print("  ├── train/OK/     (正常样本)")
        print("  ├── test/OK/      (正常测试样本)")
        print("  └── test/NG/      (异常测试样本)")
        return

    # 选择第一个可用数据进行测试
    test_data = available_data[0]
    product_name = Path(test_data).name

    print(f"\n使用数据: {test_data}")
    print(f"产品名称: {product_name}")

    # 检查anomalib是否可用
    try:
        from anomalib.engine import Engine
        from anomalib.data import Folder
        from incremental_supersimple import IncrementalSuperSimpleNet
        print("✓ Anomalib导入成功")
    except ImportError as e:
        print(f"✗ Anomalib导入失败: {e}")
        print("请确保已正确安装anomalib:")
        print("pip install anomalib")
        return

    # 显示当前队列状态
    status = get_queue_status()
    print(f"\n当前队列状态:")
    print(f"  队列大小: {status['queue_size']}")
    print(f"  当前任务: {status['current_task']['name'] if status['current_task'] else '无'}")

    # 添加训练任务
    print(f"\n添加训练任务...")
    try:
        task_id = add_training_task(
            name=product_name,
            data_root=test_data,
            force_retrain=True  # 强制重新训练
        )
        print(f"✓ 任务已添加: {task_id}")

        # 等待任务开始
        import time
        print("\n等待训练开始...")

        for i in range(30):  # 最多等待30秒
            task_info = get_task_info(task_id)
            if task_info:
                status = task_info['status']
                print(f"任务状态: {status}")

                if status == 'running':
                    print("✓ 训练已开始")
                    break
                elif status == 'completed':
                    print("✓ 训练已完成")
                    break
                elif status == 'failed':
                    print(f"✗ 训练失败: {task_info.get('error_message', '未知错误')}")
                    break

            time.sleep(1)

        # 显示最终状态
        final_info = get_task_info(task_id)
        if final_info:
            print(f"\n最终任务状态:")
            print(f"  任务ID: {final_info['task_id']}")
            print(f"  名称: {final_info['name']}")
            print(f"  状态: {final_info['status']}")
            print(f"  数据根目录: {final_info['data_root']}")
            print(f"  输出目录: {final_info['output_dir']}")

            if final_info.get('model_path'):
                print(f"  模型文件: {final_info['model_path']}")

            if final_info.get('metrics'):
                print(f"  训练指标: {final_info['metrics']}")

            if final_info.get('error_message'):
                print(f"  错误信息: {final_info['error_message']}")

    except Exception as e:
        print(f"✗ 添加任务失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_real_training()

