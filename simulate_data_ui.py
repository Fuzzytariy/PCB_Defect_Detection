#!/usr/bin/env python
import os
import random
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from PIL import Image, ImageDraw


def generate_txt_file(txt_dir, main_board, panel_id, confirmed_result, product_number, component_name,
                      output_text=None):
    """
    生成一个 TXT 文件：
      文件名格式：
         {main_board}__{panel_id}_{YYYYMMDD}_{HHMMSS}.txt
      文件内容中包含：
         - MainSN: 随机生成的主板号
         - PanelID: 固定的位号（例如 '1'、'2'、'3'、'4' 中的某个）
         - ModelName: 用户指定的产品号
         - ComponentName: 用户指定的元件名称
         - ConfirmedResult: "P"（OK批次）或 "F"（NG批次）
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    filename = f"{main_board}__{panel_id}_{date_str}_{time_str}.txt"
    filepath = os.path.join(txt_dir, filename)

    content = f"""MainSN:{main_board}
PanelSN:null
PanelID:{panel_id}
ModelName:{product_number}
ComponentName:{component_name}
Side:T
MachineName:S1
CustomerName:
Operator:HX
Programer:magicray
InspectionDate:{now.strftime("%Y/%m/%d")}
BeginTime:{now.strftime("%H:%M:%S")}
EndTime:{(now + timedelta(seconds=20)).strftime("%H:%M:%S")}
CycleTimeSec:18
InspectionBatch:A
ConfirmedResult: {"P" if confirmed_result.upper() == "P" else "F"}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    message = f"生成 TXT 文件: {filepath}\n"
    if output_text:
        output_text.insert(tk.END, message)
    else:
        print(message)
    return (main_board, panel_id), filepath


def generate_image(image_dir, main_board, component_name, panel_id, output_text=None):
    """
    生成一张 dummy 图片：
      图片命名格式为：
         BR1_{main_board}__{panel_id}.jpg
    """
    os.makedirs(image_dir, exist_ok=True)
    filename = f"{component_name}_{main_board}__{panel_id}.jpg"
    image_path = os.path.join(image_dir, filename)

    # 生成一张简单图片（200x200，背景色固定）
    img = Image.new('RGB', (200, 200), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "dummy", fill=(255, 255, 0))
    img.save(image_path)

    message = f"生成图片: {image_path}\n"
    if output_text:
        output_text.insert(tk.END, message)
    else:
        print(message)
    return image_path


def generate_category(total, confirmed_result, txt_dir, image_dir, product_number, component_name, output_text):
    """
    根据指定总数 total 生成该批次的文件：
      每块主板最多可生成 4 个文件，对应固定位号 ['1','2','3','4']。
      如果 total 不是 4 的整数倍，最后一块主板只生成剩余数量的文件。
    """
    panel_ids = ['1', '2', '3', '4']
    count = 0
    while count < total:
        # 当前主板可生成的数量（最多4个，但若剩余不足4个，则生成剩余的数量）
        images_to_generate = min(4, total - count)
        main_board = str(random.randint(2000000000, 2099999999))
        for panel in panel_ids[:images_to_generate]:
            generate_txt_file(txt_dir, main_board, panel, confirmed_result, product_number, component_name, output_text)
            generate_image(image_dir, main_board, component_name, panel, output_text)
        count += images_to_generate


def generate_data(ok_total, ng_total, product_number, component_name, output_text):
    """
    生成 OK 与 NG 批次的数据：
      - 用户输入的 ok_total/ ng_total 表示各批次需要生成的文件总数
      - 每个批次按照每块主板最多 4 个文件（对应 panel_ids = ['1','2','3','4']）划分生成
      - TXT 文件存放于 txt标注/test_YYYYMMDD 目录，图片存放于 图片数据/test_YYYYMMDD 目录
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime("%Y%m%d")
    txt_dir = os.path.join(base_dir, "txt标注", f"test_{date_str}")
    image_dir = os.path.join(base_dir, "图片数据", f"test_{date_str}")

    os.makedirs(txt_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)

    if ok_total > 0:
        generate_category(ok_total, "P", txt_dir, image_dir, product_number, component_name, output_text)
    if ng_total > 0:
        generate_category(ng_total, "F", txt_dir, image_dir, product_number, component_name, output_text)

    output_text.insert(tk.END, "数据生成完成！\n")


def run_app():
    """
    启动 Tkinter 图形界面。
    用户输入：
      - 产品号（写入 TXT 的 ModelName 字段，如 "2150155000-180-W"）
      - 元件名称（写入 TXT 的 ComponentName 字段，仅作说明）
      - OK 和 NG 的图片数量（各批次希望生成的总文件数）
    生成的文件分别保存在当天日期子目录中：
      TXT 文件在 txt标注/test_YYYYMMDD，
      图片在 图片数据/test_YYYYMMDD。
    """
    root = tk.Tk()
    root.title("模拟数据生成器")

    frame = ttk.Frame(root, padding=10)
    frame.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    ttk.Label(frame, text="【主板号和 PanelID 随机生成，每块主板最多对应 4 个文件】") \
        .grid(row=0, column=0, columnspan=2, pady=(0, 10))

    ttk.Label(frame, text="产品号:").grid(row=1, column=0, sticky=tk.W)
    product_var = tk.StringVar(value="2150155000-180-W")
    product_entry = ttk.Entry(frame, textvariable=product_var, width=20)
    product_entry.grid(row=1, column=1, pady=5)

    ttk.Label(frame, text="元件名称:").grid(row=2, column=0, sticky=tk.W)
    component_name_var = tk.StringVar(value="主板组件")
    component_name_entry = ttk.Entry(frame, textvariable=component_name_var, width=20)
    component_name_entry.grid(row=2, column=1, pady=5)

    ttk.Label(frame, text="OK 图片数量:").grid(row=3, column=0, sticky=tk.W)
    ok_var = tk.StringVar()
    ok_entry = ttk.Entry(frame, textvariable=ok_var, width=20)
    ok_entry.grid(row=3, column=1, pady=5)

    ttk.Label(frame, text="NG 图片数量:").grid(row=4, column=0, sticky=tk.W)
    ng_var = tk.StringVar()
    ng_entry = ttk.Entry(frame, textvariable=ng_var, width=20)
    ng_entry.grid(row=4, column=1, pady=5)

    output_text = tk.Text(frame, width=60, height=15)
    output_text.grid(row=6, column=0, columnspan=2, pady=10)

    def on_generate():
        product_number = product_var.get().strip()
        component_name = component_name_var.get().strip()
        try:
            ok_total = int(ok_var.get())
        except ValueError:
            output_text.insert(tk.END, "OK 图片数量请输入整数！\n")
            return
        try:
            ng_total = int(ng_var.get())
        except ValueError:
            output_text.insert(tk.END, "NG 图片数量请输入整数！\n")
            return
        if not product_number or not component_name:
            output_text.insert(tk.END, "产品号和元件名称不能为空！\n")
            return

        output_text.insert(tk.END, "开始生成数据...\n")
        generate_data(ok_total, ng_total, product_number, component_name, output_text)

    generate_btn = ttk.Button(frame, text="生成数据", command=on_generate)
    generate_btn.grid(row=5, column=0, columnspan=2, pady=10)

    root.mainloop()


if __name__ == "__main__":
    run_app()
