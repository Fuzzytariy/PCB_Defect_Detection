import os
import queue
import shutil
import threading
import time

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# 加载触发阈值配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "trigger.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
OK_THRESHOLD = cfg.get("ok_threshold", 130)
NG_THRESHOLD = cfg.get("ng_threshold", 50)


def extract_barcode_and_position_from_txt_filename(txt_filename):
    """从TXT文件名中提取条码和位置信息。"""
    base_name = os.path.splitext(os.path.basename(txt_filename))[0]
    barcode_and_position, _, _ = base_name.rsplit('_', 2)
    return barcode_and_position


def parse_txt_file(txt_file_path):
    """读取TXT文件内容，提取ModelName和ConfirmedResult。"""
    model_name = "未知产品号"
    confirmed_result = "未知复检结果"
    max_retries = 5
    for _ in range(max_retries):
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("ModelName:"):
                        model_name = line.split(":", 1)[1].strip()
                    elif line.startswith("ConfirmedResult:"):
                        confirmed_result = line.split(":", 1)[1].strip()
            break
        except PermissionError:
            time.sleep(0.5)
    return model_name, confirmed_result


def find_image_for_barcode_and_position(directory_images, barcode_and_position):
    """在图片目录中查找与条码和位置匹配的图片。"""
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue
            if os.path.splitext(filename)[0].endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images


def check_image_count(result_folder):
    ok_folder = os.path.join(result_folder, 'OK')
    ng_folder = os.path.join(result_folder, 'NG')
    ok_count = len(os.listdir(ok_folder)) if os.path.isdir(ok_folder) else 0
    ng_count = len(os.listdir(ng_folder)) if os.path.isdir(ng_folder) else 0
    return ok_count, ng_count


def process_one_image_move(image_path, model_name, confirmed_result, output_base_dir):
    result_folder = os.path.join(output_base_dir, model_name)
    ok_count, ng_count = check_image_count(result_folder)
    if confirmed_result == "P" and ok_count >= OK_THRESHOLD:
        return
    if confirmed_result == "F" and ng_count >= NG_THRESHOLD:
        return
    os.makedirs(os.path.join(result_folder, 'OK'), exist_ok=True)
    os.makedirs(os.path.join(result_folder, 'NG'), exist_ok=True)
    destination = os.path.join(
        result_folder,
        'OK' if confirmed_result == "P" else 'NG',
        os.path.basename(image_path)
    )
    shutil.copy(image_path, destination)


def process_txt_file(txt_file_path, directory_images, output_base_dir):
    barcode_and_position = extract_barcode_and_position_from_txt_filename(txt_file_path)
    model_name, confirmed_result = parse_txt_file(txt_file_path)
    image_paths = find_image_for_barcode_and_position(directory_images, barcode_and_position)
    for image_path in image_paths:
        process_one_image_move(image_path, model_name, confirmed_result, output_base_dir)


class TxtUploadHandler(FileSystemEventHandler):
    """监听TXT文件的创建事件。"""

    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.txt'):
            self.event_queue.put(event.src_path)


def worker(event_queue, directory_images, output_base_dir):
    while True:
        txt_file_path = event_queue.get()
        if txt_file_path is None:
            break
        process_txt_file(txt_file_path, directory_images, output_base_dir)
        event_queue.task_done()


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder_to_monitor_txt = os.path.join(base_dir, 'txt标注')
    directory_images = os.path.join(base_dir, '图片数据')
    output_base_dir = os.path.join(base_dir, 'output')

    event_queue = queue.Queue()
    worker_thread = threading.Thread(
        target=worker,
        args=(event_queue, directory_images, output_base_dir),
        daemon=True
    )
    worker_thread.start()

    event_handler = TxtUploadHandler(event_queue)
    observer = Observer()
    observer.schedule(event_handler, folder_to_monitor_txt, recursive=True)
    observer.start()
    print(f"开始监控 TXT 文件夹：{folder_to_monitor_txt}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    event_queue.put(None)
    worker_thread.join()


if __name__ == '__main__':
    main()
