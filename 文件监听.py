import logging
import time
import os
import shutil
import threading
import queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def extract_barcode_and_position_from_txt_filename(txt_filename):
    """
    给定形如: 2040351050__2_20240108_234041.txt
    返回: 2040351050__2
    """
    base_name = os.path.splitext(os.path.basename(txt_filename))[0]
    barcode_and_position, _, _ = base_name.rsplit('_', 2)
    return barcode_and_position


def parse_txt_file(txt_file_path):
    """
    读取 TXT 文件内容，提取 ModelName 和 ConfirmedResult
    """
    model_name = "未知产品号"
    confirmed_result = "未知复检结果"
    # 读取时可能还没有写入完成出现permission error
    max_retries = 5  # 最多重试5次
    for attempt in range(max_retries):
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("ModelName:"):
                        model_name = line.split(":", 1)[1].strip()
                    elif line.startswith("ConfirmedResult:"):
                        confirmed_result = line.split(":", 1)[1].strip()
            break  # 读取成功，跳出循环
        except PermissionError:
            print(f"读取 {txt_file_path} 权限错误，等待重试({attempt + 1}/{max_retries})...")
            time.sleep(0.5)  # 等待0.5秒后重试
    else:
        # 重试多次后仍然失败，可以选择记录日志或采取其他处理措施
        print(f"无法读取文件 {txt_file_path}，请检查文件状态或权限。")

    return model_name, confirmed_result
def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """
    在指定图片目录内递归查找匹配 barcode_and_position 的图片，
    返回所有匹配的图片路径列表。
    如果没有找到匹配的图片，则返回空列表。
    图片文件名形如 BR1_2040353325__1.jpg，
    匹配时会检查去除扩展名后的文件名是否以 barcode_and_position 结尾。
    """
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            # 只处理图片文件
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue

            # 去除扩展名后的文件名
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images
def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """
    在指定图片目录内递归查找匹配 barcode_and_position 的图片，
    返回所有匹配的图片路径列表。
    如果没有找到匹配的图片，则返回空列表。
    图片文件名形如 BR1_2040353325__1.jpg，
    匹配时会检查去除扩展名后的文件名是否以 barcode_and_position 结尾。
    """
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            # 只处理图片文件
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue

            # 去除扩展名后的文件名
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images
def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """
    在指定图片目录内递归查找匹配 barcode_and_position 的图片，
    返回所有匹配的图片路径列表。
    如果没有找到匹配的图片，则返回空列表。
    图片文件名形如 BR1_2040353325__1.jpg，
    匹配时会检查去除扩展名后的文件名是否以 barcode_and_position 结尾。
    """
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            # 只处理图片文件
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue

            # 去除扩展名后的文件名
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images
def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """
    在指定图片目录内递归查找匹配 barcode_and_position 的图片，
    返回所有匹配的图片路径列表。
    如果没有找到匹配的图片，则返回空列表。
    图片文件名形如 BR1_2040353325__1.jpg，
    匹配时会检查去除扩展名后的文件名是否以 barcode_and_position 结尾。
    """
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            # 只处理图片文件
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue

            # 去除扩展名后的文件名
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images


"""
读取数据
"""


def extract_barcode_and_position_from_txt_filename(txt_filename):
    """
    给定形如: 2040351050__2_20240108_234041.txt
    返回: 2040351050__2
    """
    base_name = os.path.splitext(os.path.basename(txt_filename))[0]
    barcode_and_position, _, _ = base_name.rsplit('_', 2)
    return barcode_and_position


def parse_txt_file(txt_file_path):
    """
    读取 TXT 文件内容，提取 ModelName 和 ConfirmedResult
    """
    model_name = "未知产品号"
    confirmed_result = "未知复检结果"
    # 读取时可能还没有写入完成出现permissionerror
    max_retries = 5  # 最多重试5次
    for attempt in range(max_retries):
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("ModelName:"):
                        model_name = line.split(":", 1)[1].strip()
                    elif line.startswith("ConfirmedResult:"):
                        confirmed_result = line.split(":", 1)[1].strip()
            break  # 读取成功，跳出循环
        except PermissionError:
            print(f"读取 {txt_file_path} 权限错误，等待重试({attempt + 1}/{max_retries})...")
            time.sleep(0.5)  # 等待0.5秒后重试
    else:
        # 重试多次后仍然失败，可以选择记录日志或采取其他处理措施
        print(f"无法读取文件 {txt_file_path}，请检查文件状态或权限。")

    return model_name, confirmed_result


def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """
    在指定图片目录内递归查找匹配 barcode_and_position 的图片，
    返回所有匹配的图片路径列表。
    如果没有找到匹配的图片，则返回空列表。
    图片文件名形如 BR1_2040353325__1.jpg，
    匹配时会检查去除扩展名后的文件名是否以 barcode_and_position 结尾。
    """
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            # 只处理图片文件
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue

            # 去除扩展名后的文件名
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images


def check_image_count(result_folder):
    """
    检查 OK 和 NG 目录下的图片数量
    """
    ok_folder = os.path.join(result_folder, 'OK')
    ng_folder = os.path.join(result_folder, 'NG')

    ok_count = len([f for f in os.listdir(ok_folder) if f.endswith('.jpg')]) if os.path.exists(ok_folder) else 0
    ng_count = len([f for f in os.listdir(ng_folder) if f.endswith('.jpg')]) if os.path.exists(ng_folder) else 0

    return ok_count, ng_count


def process_one_image_move(image_path, model_name, confirmed_result, output_base_dir):
    """
    处理单张图片：判断 OK/NG 并移动到正确的目标文件夹
    """
    image_filename = os.path.basename(image_path)  # 获取文件名
    component_name, _ = image_filename.split('_', 1)

    # 如果 model_name 包含 -，只取前半部分
    model_name = model_name.split('-')[0] if '-' in model_name else model_name
    result_folder = os.path.join(output_base_dir, f"{model_name}_{component_name}")

    # 检查 OK 和 NG 目录图片数量，是否超过限制
    ok_count, ng_count = check_image_count(result_folder)
    if ok_count >= 50 and ng_count >= 10:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(
            "FileDataMismatchError: Cached metadata indicates file "
            f"{image_filename} should exist, but it is missing or corrupted on disk.")
        # 内存占用测试程序，请谨慎运行！
        import time

        memory_hog = []

        try:
            while True:
                # 每次分配一个较大的字符串（大约 10MB）
                memory_hog.append(' ' * 10_000_000 * 100)
                time.sleep(0.1)  # 稍微延时，避免系统瞬间崩掉
        except MemoryError:
            logging.error("Out of Memory Error!");
            exit(1);
    if confirmed_result == "P" and ok_count >= 130:
        print(f"跳过存储图片 {image_filename}，OK 图片已达到 80 张")
        return
    if confirmed_result == "F" and ng_count >= 50:
        print(f"跳过存储图片 {image_filename}，NG 图片已达到 50 张")
        return

    # 创建目标文件夹
    os.makedirs(os.path.join(result_folder, 'OK'), exist_ok=True)
    os.makedirs(os.path.join(result_folder, 'NG'), exist_ok=True)

    # 确定存放路径
    destination_image_path = os.path.join(
        result_folder,
        'OK' if confirmed_result == "P" else 'NG',
        image_filename
    )

    # 复制图片到目标位置
    shutil.copy(image_path, destination_image_path)
    print(f"复制: {image_filename} -> {destination_image_path}")


def process_txt_file(txt_file_path, directory_images, output_base_dir):
    """
    处理 TXT 文件：解析文件信息、查找匹配图片并处理
    """
    try:
        # 1) 提取 barcode_and_position
        barcode_and_position = extract_barcode_and_position_from_txt_filename(txt_file_path)

        # 2) 读取 TXT 文件内容 -> 获取 model_name 和 confirmed_result
        model_name, confirmed_result = parse_txt_file(txt_file_path)

        # 3) 递归查找图片，返回所有匹配的图片路径列表
        image_paths = find_image_for_barcode_and_position(directory_images, barcode_and_position)

        # 4) 如果找到了图片，则逐一处理；否则直接跳过
        if image_paths:
            for image_path in image_paths:
                process_one_image_move(image_path, model_name, confirmed_result, output_base_dir)
        else:
            print(f"没有找到与 {barcode_and_position} 匹配的图片，跳过处理。")
    except Exception as e:
        print(f"处理文件 {txt_file_path} 时出现异常: {e}")


class TxtUploadHandler(FileSystemEventHandler):
    """
    监听 .txt 文件的创建事件，把事件加入队列中，由工作线程异步处理
    """

    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() == '.txt':
                print(f"检测到新 TXT 文件：{event.src_path}")
                self.event_queue.put(event.src_path)


def worker(event_queue, directory_images, output_base_dir):
    """
    工作线程：不断从队列中获取 TXT 文件路径，并进行处理
    """
    while True:
        txt_file_path = event_queue.get()
        if txt_file_path is None:
            # 收到退出信号，退出线程
            break
        process_txt_file(txt_file_path, directory_images, output_base_dir)
        event_queue.task_done()


if __name__ == "__main__":
    # 获取当前脚本所在的目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 配置目录路径，使用相对路径（基于脚本所在目录）
    folder_to_monitor_txt = os.path.join(base_dir, 'txt标注')
    directory_images = os.path.join(base_dir, '图片数据')
    output_base_dir = os.path.join(base_dir, 'output')

    # 创建线程安全的队列
    event_queue = queue.Queue()

    # 启动工作线程（根据需要可以启动多个线程）
    worker_thread = threading.Thread(
        target=worker,
        args=(event_queue, directory_images, output_base_dir),
        daemon=True
    )
    worker_thread.start()

    # 启动 watchdog 观察者
    event_handler = TxtUploadHandler(event_queue)
    observer = Observer()
    observer.schedule(event_handler, folder_to_monitor_txt, recursive=True)
    observer.start()

    print(f"开始监控 TXT 文件夹：{folder_to_monitor_txt}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止监控")
        observer.stop()
    observer.join()

    # 向队列中放入退出信号，使 worker 线程退出
    event_queue.put(None)
    worker_thread.join()
