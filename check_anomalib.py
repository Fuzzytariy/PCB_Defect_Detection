#!/usr/bin/env python3
"""
检查Anomalib安装状态和依赖
"""

import importlib
import sys
from pathlib import Path


def check_package(package_name, description=""):
    """检查包是否可用"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {package_name} ({version}) - {description}")
        return True
    except ImportError as e:
        print(f"✗ {package_name} - {description} - 错误: {e}")
        return False


def check_anomalib_components():
    """检查anomalib的主要组件"""
    print("检查Anomalib组件:")

    components = [
        ("anomalib", "主包"),
        ("anomalib.engine", "训练引擎"),
        ("anomalib.data", "数据模块"),
        ("anomalib.models", "模型模块"),
        ("anomalib.models.Patchcore", "PatchCore模型"),
        ("anomalib.models.EfficientAd", "EfficientAD模型"),
        ("anomalib.data.Folder", "文件夹数据集"),
    ]

    all_ok = True
    for component, desc in components:
        if not check_package(component, desc):
            all_ok = False

    return all_ok


def check_dependencies():
    """检查必要的依赖包"""
    print("\n检查依赖包:")

    dependencies = [
        ("torch", "PyTorch深度学习框架"),
        ("torchvision", "PyTorch视觉库"),
        ("lightning", "PyTorch Lightning"),
        ("opencv-python", "OpenCV图像处理"),
        ("numpy", "数值计算"),
        ("pandas", "数据处理"),
        ("yaml", "YAML配置文件"),
        ("PIL", "图像处理"),
    ]

    all_ok = True
    for dep, desc in dependencies:
        # 特殊处理一些包名
        if dep == "opencv-python":
            dep = "cv2"
        elif dep == "PIL":
            dep = "PIL"

        if not check_package(dep, desc):
            all_ok = False

    return all_ok


def test_basic_functionality():
    """测试基本功能"""
    print("\n测试基本功能:")

    try:
        # 测试导入
        from anomalib.engine import Engine
        from anomalib.data import Folder
        from anomalib.models import Patchcore, EfficientAd
        print("✓ 基本导入成功")

        # 测试创建模型
        model = Patchcore()
        print("✓ PatchCore模型创建成功")

        model = EfficientAd()
        print("✓ EfficientAD模型创建成功")

        # 测试创建引擎
        engine = Engine(max_epochs=1)
        print("✓ 训练引擎创建成功")

        return True

    except Exception as e:
        print(f"✗ 基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_config_files():
    """检查配置文件"""
    print("\n检查配置文件:")

    config_files = [
        "configs/data/pcb_folder.yaml",
        "configs/model/patchcore_pcb.yaml",
        "configs/model/efficient_ad_pcb.yaml"
    ]

    all_ok = True
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✓ {config_file}")
        else:
            print(f"✗ {config_file} - 文件不存在")
            all_ok = False

    return all_ok


def main():
    """主函数"""
    print("=" * 60)
    print("Anomalib安装检查")
    print("=" * 60)

    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()

    # 检查各个组件
    anomalib_ok = check_anomalib_components()
    deps_ok = check_dependencies()
    func_ok = test_basic_functionality()
    config_ok = check_config_files()

    print("\n" + "=" * 60)
    print("检查结果:")
    print(f"  Anomalib组件: {'✓ 正常' if anomalib_ok else '✗ 异常'}")
    print(f"  依赖包: {'✓ 正常' if deps_ok else '✗ 异常'}")
    print(f"  基本功能: {'✓ 正常' if func_ok else '✗ 异常'}")
    print(f"  配置文件: {'✓ 正常' if config_ok else '✗ 异常'}")

    if all([anomalib_ok, deps_ok, func_ok, config_ok]):
        print("\n🎉 所有检查通过，可以开始训练！")
        return True
    else:
        print("\n❌ 存在问题，请解决后再进行训练")

        if not anomalib_ok:
            print("\n安装Anomalib:")
            print("pip install anomalib")

        if not deps_ok:
            print("\n安装缺失的依赖包")

        return False


if __name__ == "__main__":
    main()

