#!/usr/bin/env python3
"""
服务启动脚本
可以启动API服务和文件监听服务
"""

import os
import sys
import time
import signal
import subprocess
import threading
import argparse
from pathlib import Path


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_api_service(self, host="0.0.0.0", port=5000, debug=False):
        """启动API服务"""
        cmd = [
            sys.executable, "训练API服务.py",
            "--host", host,
            "--port", str(port)
        ]
        
        if debug:
            cmd.append("--debug")
        
        print(f"🚀 启动API服务: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes['api'] = process
            
            # 启动日志输出线程
            def log_output():
                for line in process.stdout:
                    if self.running:
                        print(f"[API] {line.rstrip()}")
            
            threading.Thread(target=log_output, daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"❌ 启动API服务失败: {e}")
            return False
    
    def start_file_monitor(self):
        """启动文件监听服务"""
        cmd = [sys.executable, "训练目录监听.py"]
        
        print(f"📁 启动文件监听服务: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes['monitor'] = process
            
            # 启动日志输出线程
            def log_output():
                for line in process.stdout:
                    if self.running:
                        print(f"[监听] {line.rstrip()}")
            
            threading.Thread(target=log_output, daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"❌ 启动文件监听服务失败: {e}")
            return False
    
    def stop_all_services(self):
        """停止所有服务"""
        print("\n🛑 正在停止所有服务...")
        self.running = False
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                print(f"停止 {name} 服务...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"强制终止 {name} 服务...")
                    process.kill()
                except Exception as e:
                    print(f"停止 {name} 服务时出错: {e}")
        
        print("✅ 所有服务已停止")
    
    def wait_for_services(self):
        """等待服务运行"""
        try:
            while self.running:
                # 检查进程状态
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"⚠️ {name} 服务已退出")
                        del self.processes[name]
                
                if not self.processes:
                    print("所有服务都已退出")
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n收到中断信号...")
        finally:
            self.stop_all_services()


def check_dependencies():
    """检查依赖"""
    required_files = [
        "训练API服务.py",
        "训练目录监听.py", 
        "训练任务管理器.py",
        "算法端.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必需文件:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    # 检查Python包
    try:
        import flask
        import anomalib
        import watchdog
        print("✅ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少Python包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def main():
    parser = argparse.ArgumentParser(description="训练服务启动器")
    parser.add_argument("--api-only", action="store_true", help="仅启动API服务")
    parser.add_argument("--monitor-only", action="store_true", help="仅启动文件监听服务")
    parser.add_argument("--host", default="0.0.0.0", help="API服务地址")
    parser.add_argument("--port", type=int, default=5000, help="API服务端口")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--no-check", action="store_true", help="跳过依赖检查")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 训练任务管理系统启动器")
    print("=" * 60)
    
    # 检查依赖
    if not args.no_check and not check_dependencies():
        sys.exit(1)
    
    # 创建服务管理器
    manager = ServiceManager()
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}")
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    services_started = 0
    
    if not args.monitor_only:
        if manager.start_api_service(args.host, args.port, args.debug):
            services_started += 1
            print(f"✅ API服务已启动: http://{args.host}:{args.port}")
        else:
            print("❌ API服务启动失败")
    
    if not args.api_only:
        if manager.start_file_monitor():
            services_started += 1
            print("✅ 文件监听服务已启动")
        else:
            print("❌ 文件监听服务启动失败")
    
    if services_started == 0:
        print("❌ 没有服务成功启动")
        sys.exit(1)
    
    print(f"\n🎉 成功启动 {services_started} 个服务")
    print("按 Ctrl+C 停止所有服务")
    
    # 等待服务运行
    manager.wait_for_services()


if __name__ == "__main__":
    main()