#!/usr/bin/env python3
"""
训练任务状态查看器
用于查看当前训练任务的状态和队列情况
"""

import argparse
import json
from datetime import datetime
from 训练任务管理器 import task_manager, TaskStatus


def format_datetime(dt_str):
    """格式化日期时间字符串"""
    if not dt_str:
        return "未设置"
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def show_queue_status():
    """显示队列状态"""
    status = task_manager.get_queue_status()
    
    print("=" * 60)
    print("训练任务队列状态")
    print("=" * 60)
    
    # 当前正在执行的任务
    if status['current_task']:
        current = status['current_task']
        print(f"🔄 正在执行任务:")
        print(f"   任务ID: {current['task_id']}")
        print(f"   任务名称: {current['name']}")
        print(f"   开始时间: {format_datetime(current['started_at'])}")
    else:
        print("🔄 当前没有正在执行的任务")
    
    print()
    
    # 等待中的任务
    print(f"⏳ 等待队列中的任务数: {status['queue_size']}")
    if status['pending_tasks']:
        print("   等待中的任务:")
        for i, task in enumerate(status['pending_tasks'], 1):
            print(f"   {i}. {task['name']} (ID: {task['task_id']}) - 创建于 {format_datetime(task['created_at'])}")
    else:
        print("   队列为空")
    
    print()


def show_task_detail(task_id):
    """显示任务详细信息"""
    task_info = task_manager.get_task_info(task_id)
    
    if not task_info:
        print(f"❌ 未找到任务ID: {task_id}")
        return
    
    print("=" * 60)
    print(f"任务详细信息: {task_info['name']}")
    print("=" * 60)
    
    status_emoji = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "🚫"
    }
    
    print(f"任务ID: {task_info['task_id']}")
    print(f"任务名称: {task_info['name']}")
    print(f"数据路径: {task_info['root']}")
    print(f"状态: {status_emoji.get(task_info['status'], '❓')} {task_info['status'].upper()}")
    print(f"创建时间: {format_datetime(task_info['created_at'])}")
    print(f"开始时间: {format_datetime(task_info['started_at'])}")
    print(f"完成时间: {format_datetime(task_info['completed_at'])}")
    
    if task_info['error_message']:
        print(f"错误信息: {task_info['error_message']}")
    
    # 计算执行时间
    if task_info['started_at'] and task_info['completed_at']:
        try:
            start_time = datetime.fromisoformat(task_info['started_at'])
            end_time = datetime.fromisoformat(task_info['completed_at'])
            duration = end_time - start_time
            print(f"执行时长: {duration}")
        except:
            pass
    
    print()


def show_all_tasks():
    """显示所有任务"""
    print("=" * 80)
    print("所有训练任务")
    print("=" * 80)
    
    status_emoji = {
        "pending": "⏳",
        "running": "🔄", 
        "completed": "✅",
        "failed": "❌",
        "cancelled": "🚫"
    }
    
    # 按状态分组显示
    status_groups = {
        TaskStatus.RUNNING: [],
        TaskStatus.PENDING: [],
        TaskStatus.COMPLETED: [],
        TaskStatus.FAILED: [],
        TaskStatus.CANCELLED: []
    }
    
    for task_id, task in task_manager.tasks.items():
        status_groups[task.status].append(task)
    
    # 显示各状态的任务
    for status, tasks in status_groups.items():
        if not tasks:
            continue
            
        print(f"\n{status_emoji.get(status.value, '❓')} {status.value.upper()} ({len(tasks)}个任务):")
        print("-" * 40)
        
        for task in sorted(tasks, key=lambda x: x.created_at, reverse=True):
            created_time = task.created_at.strftime("%m-%d %H:%M")
            print(f"  {task.name:<20} | {task.task_id} | {created_time}")
            if task.error_message:
                print(f"    错误: {task.error_message[:50]}...")
    
    print()


def save_tasks_report(filename):
    """保存任务报告到文件"""
    task_manager.save_tasks_to_file(filename)
    print(f"✅ 任务报告已保存到: {filename}")


def cancel_task(task_id):
    """取消任务"""
    success = task_manager.cancel_task(task_id)
    if success:
        print(f"✅ 任务 {task_id} 已取消")
    else:
        print(f"❌ 无法取消任务 {task_id}")


def main():
    parser = argparse.ArgumentParser(description="训练任务状态查看器")
    parser.add_argument("--queue", "-q", action="store_true", help="显示队列状态")
    parser.add_argument("--all", "-a", action="store_true", help="显示所有任务")
    parser.add_argument("--task", "-t", type=str, help="显示指定任务的详细信息")
    parser.add_argument("--save", "-s", type=str, help="保存任务报告到文件")
    parser.add_argument("--cancel", "-c", type=str, help="取消指定的任务")
    parser.add_argument("--watch", "-w", action="store_true", help="持续监控队列状态")
    
    args = parser.parse_args()
    
    if args.queue:
        show_queue_status()
    elif args.all:
        show_all_tasks()
    elif args.task:
        show_task_detail(args.task)
    elif args.save:
        save_tasks_report(args.save)
    elif args.cancel:
        cancel_task(args.cancel)
    elif args.watch:
        import time
        print("🔍 持续监控模式 (按 Ctrl+C 退出)")
        try:
            while True:
                print("\033[2J\033[H")  # 清屏
                show_queue_status()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
    else:
        # 默认显示队列状态
        show_queue_status()


if __name__ == "__main__":
    main()