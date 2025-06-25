#!/usr/bin/env python3
"""
手动训练工具
用于手动添加训练任务到队列
"""

import os
import argparse
from 训练任务管理器 import add_training_task, get_queue_status


def validate_data_directory(data_path):
    """验证数据目录结构"""
    if not os.path.exists(data_path):
        return False, f"数据目录不存在: {data_path}"
    
    # 检查必要的子目录
    train_ok = os.path.join(data_path, "train", "OK")
    test_ok = os.path.join(data_path, "test", "OK")
    test_ng = os.path.join(data_path, "test", "NG")
    
    missing_dirs = []
    if not os.path.exists(train_ok):
        missing_dirs.append("train/OK")
    if not os.path.exists(test_ok):
        missing_dirs.append("test/OK")
    if not os.path.exists(test_ng):
        missing_dirs.append("test/NG")
    
    if missing_dirs:
        return False, f"缺少必要的目录: {', '.join(missing_dirs)}"
    
    # 检查图片数量
    train_ok_count = len([f for f in os.listdir(train_ok) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
    test_ok_count = len([f for f in os.listdir(test_ok) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
    test_ng_count = len([f for f in os.listdir(test_ng) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
    
    if train_ok_count == 0:
        return False, "train/OK 目录中没有图片文件"
    if test_ok_count == 0:
        return False, "test/OK 目录中没有图片文件"
    if test_ng_count == 0:
        return False, "test/NG 目录中没有图片文件"
    
    return True, f"数据验证通过 - 训练集OK: {train_ok_count}张, 测试集OK: {test_ok_count}张, 测试集NG: {test_ng_count}张"


def interactive_mode():
    """交互式模式"""
    print("=" * 60)
    print("🚀 手动训练任务添加工具 - 交互模式")
    print("=" * 60)
    
    # 获取数据目录
    while True:
        data_path = input("\n请输入数据目录路径: ").strip()
        if not data_path:
            print("❌ 数据目录路径不能为空")
            continue
        
        # 支持相对路径
        if not os.path.isabs(data_path):
            data_path = os.path.abspath(data_path)
        
        valid, message = validate_data_directory(data_path)
        if valid:
            print(f"✅ {message}")
            break
        else:
            print(f"❌ {message}")
            retry = input("是否重新输入? (y/n): ").strip().lower()
            if retry != 'y':
                return
    
    # 获取任务名称
    default_name = os.path.basename(data_path)
    task_name = input(f"\n请输入任务名称 (默认: {default_name}): ").strip()
    if not task_name:
        task_name = default_name
    
    # 获取骨干网络
    print("\n可选的骨干网络:")
    backbones = ["resnet18", "resnet34", "resnet50", "wide_resnet50_2"]
    for i, backbone in enumerate(backbones, 1):
        print(f"  {i}. {backbone}")
    
    while True:
        backbone_choice = input(f"请选择骨干网络 (1-{len(backbones)}, 默认: 1): ").strip()
        if not backbone_choice:
            backbone = backbones[0]
            break
        try:
            choice_idx = int(backbone_choice) - 1
            if 0 <= choice_idx < len(backbones):
                backbone = backbones[choice_idx]
                break
            else:
                print(f"❌ 请输入 1-{len(backbones)} 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
    
    # 获取特征层
    print("\n特征层配置:")
    print("  1. ['layer1', 'layer2', 'layer3'] (默认)")
    print("  2. ['layer2', 'layer3']")
    print("  3. ['layer3']")
    print("  4. 自定义")
    
    while True:
        layer_choice = input("请选择特征层配置 (1-4, 默认: 1): ").strip()
        if not layer_choice or layer_choice == "1":
            layers = ['layer1', 'layer2', 'layer3']
            break
        elif layer_choice == "2":
            layers = ['layer2', 'layer3']
            break
        elif layer_choice == "3":
            layers = ['layer3']
            break
        elif layer_choice == "4":
            custom_layers = input("请输入特征层 (用逗号分隔, 如: layer1,layer2): ").strip()
            if custom_layers:
                layers = [layer.strip() for layer in custom_layers.split(',')]
                break
            else:
                print("❌ 自定义特征层不能为空")
        else:
            print("❌ 请输入 1-4 之间的数字")
    
    # 获取其他参数
    print("\n高级参数 (可直接回车使用默认值):")
    
    # 核心集采样比例
    while True:
        coreset_input = input("核心集采样比例 (默认: 0.1): ").strip()
        if not coreset_input:
            coreset_sampling_ratio = 0.1
            break
        try:
            coreset_sampling_ratio = float(coreset_input)
            if 0 < coreset_sampling_ratio <= 1:
                break
            else:
                print("❌ 采样比例应在 0-1 之间")
        except ValueError:
            print("❌ 请输入有效的数字")
    
    # 邻居数量
    while True:
        neighbors_input = input("邻居数量 (默认: 9): ").strip()
        if not neighbors_input:
            num_neighbors = 9
            break
        try:
            num_neighbors = int(neighbors_input)
            if num_neighbors > 0:
                break
            else:
                print("❌ 邻居数量应大于 0")
        except ValueError:
            print("❌ 请输入有效的整数")
    
    # 确认信息
    print("\n" + "=" * 60)
    print("📋 任务配置确认")
    print("=" * 60)
    print(f"任务名称: {task_name}")
    print(f"数据路径: {data_path}")
    print(f"骨干网络: {backbone}")
    print(f"特征层: {layers}")
    print(f"核心集采样比例: {coreset_sampling_ratio}")
    print(f"邻居数量: {num_neighbors}")
    
    confirm = input("\n确认添加任务? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 任务已取消")
        return
    
    # 添加任务
    try:
        task_id = add_training_task(
            name=task_name,
            root=data_path,
            backbone=backbone,
            layers=layers,
            coreset_sampling_ratio=coreset_sampling_ratio,
            num_neighbors=num_neighbors
        )
        
        print(f"\n✅ 训练任务已添加成功!")
        print(f"任务ID: {task_id}")
        print(f"任务名称: {task_name}")
        
        # 显示队列状态
        queue_status = get_queue_status()
        print(f"\n📊 当前队列状态:")
        print(f"等待任务数: {queue_status['queue_size']}")
        if queue_status['current_task']:
            print(f"正在执行: {queue_status['current_task']['name']}")
        else:
            print("当前没有正在执行的任务")
            
    except Exception as e:
        print(f"❌ 添加任务失败: {e}")


def command_line_mode(args):
    """命令行模式"""
    # 验证数据目录
    data_path = os.path.abspath(args.data_path)
    valid, message = validate_data_directory(data_path)
    if not valid:
        print(f"❌ {message}")
        return
    
    print(f"✅ {message}")
    
    # 解析特征层
    if args.layers:
        layers = [layer.strip() for layer in args.layers.split(',')]
    else:
        layers = ['layer1', 'layer2', 'layer3']
    
    # 添加任务
    try:
        task_id = add_training_task(
            name=args.name or os.path.basename(data_path),
            root=data_path,
            backbone=args.backbone,
            layers=layers,
            coreset_sampling_ratio=args.coreset_ratio,
            num_neighbors=args.neighbors
        )
        
        print(f"\n✅ 训练任务已添加成功!")
        print(f"任务ID: {task_id}")
        print(f"任务名称: {args.name or os.path.basename(data_path)}")
        
        # 显示队列状态
        if not args.quiet:
            queue_status = get_queue_status()
            print(f"\n📊 当前队列状态:")
            print(f"等待任务数: {queue_status['queue_size']}")
            if queue_status['current_task']:
                print(f"正在执行: {queue_status['current_task']['name']}")
            
    except Exception as e:
        print(f"❌ 添加任务失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="手动训练任务添加工具")
    parser.add_argument("data_path", nargs="?", help="数据目录路径")
    parser.add_argument("--name", "-n", type=str, help="任务名称")
    parser.add_argument("--backbone", "-b", type=str, default="resnet18", 
                       choices=["resnet18", "resnet34", "resnet50", "wide_resnet50_2"],
                       help="骨干网络 (默认: resnet18)")
    parser.add_argument("--layers", "-l", type=str, help="特征层，用逗号分隔 (默认: layer1,layer2,layer3)")
    parser.add_argument("--coreset-ratio", "-cr", type=float, default=0.1,
                       help="核心集采样比例 (默认: 0.1)")
    parser.add_argument("--neighbors", "-nb", type=int, default=9,
                       help="邻居数量 (默认: 9)")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式，不显示队列状态")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    if args.interactive or not args.data_path:
        interactive_mode()
    else:
        command_line_mode(args)


if __name__ == "__main__":
    main()