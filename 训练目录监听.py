import logging
import os
import random
import shutil
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# 导入训练任务管理器
from 训练任务管理器 import add_training_task, get_queue_status


def organize_data(source_dir, dest_dir, product_component, seed=None):
    """
    数据整理：从 source_dir 下的 OK 和 NG 子文件夹中分别读取图片，
    按要求随机抽取样本后移动到目标训练集和测试集目录中。

    参数：
    - source_dir: 源图片所在目录（某个产品号+元件名文件夹，内含 OK 和 NG 子文件夹）
    - dest_dir: 数据存储的根目录（如 "/data"）
    - product_component: 产品号+元件名，用于创建对应的目录结构
    - seed: 随机种子（可选），保证结果可重复性
    """
    # 定义源 OK 和 NG 文件夹路径
    ok_source_dir = os.path.join(source_dir, "OK")
    ng_source_dir = os.path.join(source_dir, "NG")

    # 获取 OK 和 NG 文件夹中所有图片文件（假设仅包含图片）
    ok_files = os.listdir(ok_source_dir) if os.path.isdir(ok_source_dir) else []
    ng_files = os.listdir(ng_source_dir) if os.path.isdir(ng_source_dir) else []

    # 判断是否满足数量要求
    if len(ok_files) < 130:
        raise ValueError(f"{product_component} 内 OK 图片数量不足：{len(ok_files)}张")
    if len(ng_files) < 50:
        raise ValueError(f"{product_component} 内 NG 图片数量不足：{len(ng_files)}张")

    # 设置随机种子，确保抽样结果可重复
    if seed is not None:
        random.seed(seed)

    # 如果 OK 图片超过 130 张，则随机抽取 130 张
    if len(ok_files) > 130:
        ok_files = random.sample(ok_files, 130)

    # 从 130 张 OK 图片中随机抽取 80 张作为训练集，剩余 50 张作为测试集
    train_ok = random.sample(ok_files, 80)
    test_ok = [f for f in ok_files if f not in train_ok]

    # NG 图片：若超过 50 张，则随机抽取 50 张；否则全部使用
    if len(ng_files) > 50:
        test_ng = random.sample(ng_files, 50)
    else:
        test_ng = ng_files

    # 定义目标目录结构
    train_ok_dir = os.path.join(dest_dir, product_component, "train", "OK")
    test_ok_dir = os.path.join(dest_dir, product_component, "test", "OK")
    test_ng_dir = os.path.join(dest_dir, product_component, "test", "NG")

    # 自动创建目标目录（若不存在则创建）
    os.makedirs(train_ok_dir, exist_ok=True)
    os.makedirs(test_ok_dir, exist_ok=True)
    os.makedirs(test_ng_dir, exist_ok=True)

    # 将 OK 训练集图片从 ok_source_dir 移动到目标目录
    for f in train_ok:
        src_path = os.path.join(ok_source_dir, f)
        dst_path = os.path.join(train_ok_dir, f)
        shutil.move(src_path, dst_path)

    # 将 OK 测试集图片从 ok_source_dir 移动到目标目录
    for f in test_ok:
        src_path = os.path.join(ok_source_dir, f)
        dst_path = os.path.join(test_ok_dir, f)
        shutil.move(src_path, dst_path)

    # 将 NG 测试集图片从 ng_source_dir 移动到目标目录
    for f in test_ng:
        src_path = os.path.join(ng_source_dir, f)
        dst_path = os.path.join(test_ng_dir, f)
        shutil.move(src_path, dst_path)

    logging.info(
        f"整理完成【{product_component}】：训练集 OK {len(train_ok)}张，测试集 OK {len(test_ok)}张，测试集 NG {len(test_ng)}张")

    return {"train_OK": len(train_ok), "test_OK": len(test_ok), "test_NG": len(test_ng)}


class ProductFolderHandler(FileSystemEventHandler):
    """
    使用 watchdog 监听 output 目录下产品号+元件名文件夹的变化，
    当某个文件夹内的 OK 和 NG 图片满足数量要求时，进行数据整理并记录处理过的文件夹。
    """

    def __init__(self, source_parent_dir, dest_dir, processed_file, seed=None):
        self.source_parent_dir = source_parent_dir
        self.dest_dir = dest_dir
        self.processed_file = processed_file
        self.seed = seed
        self.processed = set()
        self.update_processed_set()  # 初始化时加载记录

    def update_processed_set(self):
        """重新读取记录文件，更新 self.processed 集合"""
        if os.path.exists(self.processed_file):
            with open(self.processed_file, 'r', encoding='utf-8') as f:
                self.processed = set(line.strip() for line in f)
        else:
            self.processed = set()

    def process_folder(self, product_component):
        product_component_path = os.path.join(self.source_parent_dir, product_component)
        if not os.path.isdir(product_component_path):
            return

        # 重新加载记录，确保处理记录是最新的
        self.update_processed_set()

        # 定义 OK 和 NG 文件夹的路径
        ok_folder = os.path.join(product_component_path, "OK")
        ng_folder = os.path.join(product_component_path, "NG")

        # 如果文件夹不存在，则计数为 0
        ok_count = len(os.listdir(ok_folder)) if os.path.isdir(ok_folder) else 0
        ng_count = len(os.listdir(ng_folder)) if os.path.isdir(ng_folder) else 0

        if ok_count >= 130 and ng_count >= 50:
            logging.info(f"检测到【{product_component}】满足要求：OK {ok_count}张，NG {ng_count}张")
            if product_component in self.processed:
                logging.info(f"【{product_component}】已处理，跳过")
                return
            try:
                # 调用数据整理函数
                stats = organize_data(product_component_path, self.dest_dir, product_component, self.seed)

                # 更新内存和记录文件
                self.processed.add(product_component)
                with open(self.processed_file, 'a', encoding='utf-8') as f:
                    f.write(product_component + "\n")

                logging.info(f"【{product_component}】处理成功，并记录在 {self.processed_file} 中")

                # 数据整理完成后，添加训练任务到队列
                data_root = os.path.join(self.dest_dir, product_component)
                task_id = add_training_task(
                    name=product_component,
                    root=data_root,
                    backbone="resnet18",
                    layers=['layer1', 'layer2', 'layer3'],
                    coreset_sampling_ratio=0.1,
                    num_neighbors=9
                )

                logging.info(f"【{product_component}】训练任务已添加到队列，任务ID: {task_id}")

                # 打印当前队列状态
                queue_status = get_queue_status()
                logging.info(f"当前训练队列状态: 等待任务数={queue_status['queue_size']}")
                if queue_status['current_task']:
                    logging.info(f"正在执行任务: {queue_status['current_task']['name']}")

            except Exception as e:
                logging.error(f"【{product_component}】处理失败：{e}")
        else:
            logging.debug(f"【{product_component}】未满足数量要求：OK {ok_count}张, NG {ng_count}张")

    def on_any_event(self, event):
        """
        每当目录下有任意事件（文件创建、修改等），提取事件路径所属的产品号+元件名文件夹并尝试处理
        """
        event_path = event.src_path
        try:
            rel_path = os.path.relpath(event_path, self.source_parent_dir)
        except ValueError:
            return
        parts = rel_path.split(os.sep)
        if len(parts) >= 1:
            product_component = parts[0]
            self.process_folder(product_component)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # 定义源目录、目标目录和记录文件路径
    source_parent_dir = os.path.join(base_dir, "output")  # 存放各个产品号+元件名文件夹
    if not os.path.exists(source_parent_dir):
        os.makedirs(source_parent_dir)
    dest_dir = os.path.join(base_dir, "data")  # 整理后数据存放目录
    processed_file = os.path.join(base_dir, "processed.txt")  # 用于记录已处理的产品目录
    seed = 42  # 随机种子

    event_handler = ProductFolderHandler(source_parent_dir, dest_dir, processed_file, seed)
    observer = Observer()
    # 递归监听 source_parent_dir 下的所有文件和文件夹变化
    observer.schedule(event_handler, path=source_parent_dir, recursive=True)
    observer.start()
    logging.info("启动 watchdog 监听器，等待文件变化触发处理...")
    logging.info("训练任务管理器已启动，所有训练任务将串行执行")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
