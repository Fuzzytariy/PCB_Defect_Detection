import os
import shutil
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# 基础目录
BASE_DIR = Path(__file__).parent
TXT_DIR = BASE_DIR / "txt标注"
IMAGE_DIR = BASE_DIR / "图片数据"
OUTPUT_DIR = BASE_DIR / "output"


def extract_barcode_and_position_from_txt_filename(txt_filename: str) -> str:
    """从TXT文件名中提取条码和位置信息"""
    base_name = Path(txt_filename).stem
    barcode_and_position, _, _ = base_name.rsplit('_', 2)
    return barcode_and_position


def parse_txt_file(txt_file_path: str):
    """解析TXT文件，获取ModelName和ConfirmedResult"""
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


def find_image_for_barcode_and_position(directory_images: Path, barcode_and_position: str):
    """在图片目录中查找匹配条码的所有图片"""
    matched_images = []
    for root, _, files in os.walk(directory_images):
        for filename in files:
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue
            if Path(filename).stem.endswith(barcode_and_position):
                matched_images.append(os.path.join(root, filename))
    return matched_images


def process_one_image_move(image_path: str, model_name: str, confirmed_result: str, output_base_dir: Path):
    """根据标注结果复制图片到对应目录"""
    image_filename = os.path.basename(image_path)
    component_name, _ = image_filename.split('_', 1)
    model_name = model_name.split('-')[0] if '-' in model_name else model_name
    result_folder = output_base_dir / f"{model_name}_{component_name}"
    (result_folder / 'OK').mkdir(parents=True, exist_ok=True)
    (result_folder / 'NG').mkdir(parents=True, exist_ok=True)
    destination = result_folder / ('OK' if confirmed_result == 'P' else 'NG') / image_filename
    shutil.copy(image_path, destination)
    print(f"复制: {image_filename} -> {destination}")


def process_txt_file(txt_file_path: str, directory_images: Path, output_base_dir: Path):
    """处理单个TXT文件"""
    try:
        barcode_and_position = extract_barcode_and_position_from_txt_filename(txt_file_path)
        model_name, confirmed_result = parse_txt_file(txt_file_path)
        image_paths = find_image_for_barcode_and_position(directory_images, barcode_and_position)
        if image_paths:
            for image_path in image_paths:
                process_one_image_move(image_path, model_name, confirmed_result, output_base_dir)
        else:
            print(f"没有找到与 {barcode_and_position} 匹配的图片，跳过处理。")
    except Exception as e:
        print(f"处理文件 {txt_file_path} 时出现异常: {e}")


class TxtUploadHandler(FileSystemEventHandler):
    """监听TXT文件创建事件"""

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.txt'):
            print(f"检测到新 TXT 文件：{event.src_path}")
            process_txt_file(event.src_path, IMAGE_DIR, OUTPUT_DIR)


def main():
    TXT_DIR.mkdir(exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    event_handler = TxtUploadHandler()
    observer = Observer()
    observer.schedule(event_handler, str(TXT_DIR), recursive=False)
    observer.start()
    print("启动 watchdog 监听器，等待TXT文件...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
