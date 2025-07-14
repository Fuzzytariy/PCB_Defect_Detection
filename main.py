#!/usr/bin/env python3
"""
PCB缺陷检测训练系统主启动脚本
整合文件监听、训练目录监听和Web界面
"""

import signal
import sys
import threading
import time
from pathlib import Path


def start_file_monitor():
    """启动文件监听器"""
    print("启动PCB文件监听器...")
    try:
        import 文件监听
        文件监听.main()
    except Exception as e:
        print(f"文件监听器启动失败: {e}")


def start_training_monitor():
    """启动训练目录监听器"""
    print("启动训练目录监听器...")
    try:
        import 训练目录监听
        训练目录监听.main()
    except Exception as e:
        print(f"训练目录监听器启动失败: {e}")


def start_web_interface():
    """启动Web界面"""
    print("启动Web监控界面...")
    try:
        # 优先使用增强版Web界面
        from web_interface_enhanced import app
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"增强版Web界面启动失败，尝试基础版: {e}")
        try:
            from web_interface import app
            app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        except Exception as e2:
            print(f"Web界面启动失败: {e2}")


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号，正在关闭系统...")
    sys.exit(0)


def main():
    """主函数"""
    print("=" * 60)
    print("PCB缺陷检测训练系统")
    print("=" * 60)
    print("系统组件:")
    print("1. PCB文件监听器 - 监听TXT标注文件，自动整理图片数据")
    print("2. 训练目录监听器 - 监听数据目录，自动触发训练任务")
    print("3. 训练系统 - 基于Anomalib的异常检测模型训练")
    print("4. Web监控界面 - 实时监控训练状态和结果")
    print("=" * 60)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 检查必要的目录
    base_dir = Path(__file__).parent
    required_dirs = [
        base_dir / "txt标注",
        base_dir / "图片数据",
        base_dir / "output",
        base_dir / "data",
        base_dir / "configs"
    ]

    for dir_path in required_dirs:
        dir_path.mkdir(exist_ok=True)
        print(f"✓ 目录检查: {dir_path}")

    # 检查配置文件
    config_files = [
        base_dir / "configs" / "data" / "pcb_folder.yaml",
        base_dir / "configs" / "model" / "patchcore_pcb.yaml",
    ]

    for config_file in config_files:
        if config_file.exists():
            print(f"✓ 配置文件: {config_file}")
        else:
            print(f"✗ 配置文件缺失: {config_file}")

    print("\n启动系统组件...")

    # 启动各个组件的线程
    threads = []

    # 文件监听器线程
    file_monitor_thread = threading.Thread(
        target=start_file_monitor,
        name="FileMonitor",
        daemon=True
    )
    threads.append(file_monitor_thread)

    # 训练目录监听器线程
    training_monitor_thread = threading.Thread(
        target=start_training_monitor,
        name="TrainingMonitor",
        daemon=True
    )
    threads.append(training_monitor_thread)

    # Web界面线程
    web_thread = threading.Thread(
        target=start_web_interface,
        name="WebInterface",
        daemon=True
    )
    threads.append(web_thread)

    # 启动所有线程
    for thread in threads:
        thread.start()
        print(f"✓ 启动组件: {thread.name}")
        time.sleep(1)  # 错开启动时间

    print("\n" + "=" * 60)
    print("系统启动完成！")
    print("增强版Web监控界面: http://localhost:5001")
    print("基础版Web监控界面: http://localhost:5000")
    print("按 Ctrl+C 停止系统")
    print("=" * 60)

    try:
        # 主线程保持运行
        while True:
            time.sleep(1)

            # 检查线程状态
            for thread in threads:
                if not thread.is_alive():
                    print(f"警告: 组件 {thread.name} 已停止")

    except KeyboardInterrupt:
        print("\n正在停止系统...")
    except Exception as e:
        print(f"系统异常: {e}")
    finally:
        print("系统已停止")


if __name__ == "__main__":
    main()

