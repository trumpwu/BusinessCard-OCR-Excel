import os
import sys
import glob
import cv2
import numpy as np
import pymupdf

# Ensure UTF-8 console output
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.card_parser import parse_card_fields
from src.excel_exporter import export_to_excel

def locate_ocr_plugin():
    """搜尋本機已就緒的 PaddleOCR-json 引擎"""
    search_paths = [
        r"D:\project\Umi-OCR\Umi-OCR_Paddle_v2.1.5\UmiOCR-data\plugins\win7_x64_PaddleOCR-json",
        os.path.join(BASE_DIR, "engine", "win7_x64_PaddleOCR-json"),
        os.path.join(BASE_DIR, "Umi-OCR", "UmiOCR-data", "plugins", "win7_x64_PaddleOCR-json"),
    ]
    for p in search_paths:
        if os.path.exists(os.path.join(p, "PaddleOCR-json.exe")):
            return p
    return None

def process_file(input_file: str, base_output_dir: str):
    ocr_dir = locate_ocr_plugin()
    if not ocr_dir:
        print("[❌ 錯誤] 找不到 PaddleOCR-json 核心引擎！請確認已解壓縮 Umi-OCR 或執行 install.bat。")
        sys.exit(1)

    if ocr_dir not in sys.path:
        sys.path.append(ocr_dir)
    from PPOCR_api import PPOCR_pipe

    os.makedirs(base_output_dir, exist_ok=True)
    cards_img_dir = os.path.join(base_output_dir, "裁切名片圖檔")
    os.makedirs(cards_img_dir, exist_ok=True)
    temp_pages_dir = os.path.join(base_output_dir, "temp_pages")
    os.makedirs(temp_pages_dir, exist_ok=True)

    filename_no_ext = os.path.splitext(os.path.basename(input_file))[0]
    print(f"\n=======================================================")
    print(f"  🚀 開始名片自動裁切辨識與歸檔：{os.path.basename(input_file)}")
    print(f"=======================================================")

    ocr_exe = os.path.join(ocr_dir, "PaddleOCR-json.exe")
    ocr = PPOCR_pipe(ocr_exe, argument={"config_path": "models/config_chinese_cht.txt"})

    pages_images = []
    if input_file.lower().endswith(".pdf"):
        doc = pymupdf.open(input_file)
        print(f"[*] PDF 總頁數: {len(doc)} 頁")
        for page_idx, page in enumerate(doc):
            imgs = page.get_images()
            if imgs:
                xref = imgs[0][0]
                base_img = doc.extract_image(xref)
                p_path = os.path.join(temp_pages_dir, f"page_{page_idx+1:02d}.jpg")
                with open(p_path, "wb") as f:
                    f.write(base_img["image"])
                pages_images.append((page_idx + 1, p_path))
    else:
        pages_images.append((1, input_file))

    all_cards_data = []
    card_counter = 0

    for page_num, page_img_path in pages_images:
        print(f"[*] 正在分析第 {page_num} 頁...")
        page_bgr = cv2.imdecode(np.fromfile(page_img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if page_bgr is None:
            continue
        ph, pw = page_bgr.shape[:2]

        res = ocr.run(page_img_path)
        lines = res.get("data", [])
        if not lines:
            continue

        boxes = []
        for l_idx, l in enumerate(lines):
            b = l["box"]
            xs = [pt[0] for pt in b]
            ys = [pt[1] for pt in b]
            boxes.append({
                "id": l_idx,
                "x1": min(xs), "y1": min(ys),
                "x2": max(xs), "y2": max(ys),
                "text": l["text"]
            })

        # 空間鄰近聚合 (Spatial Clustering)
        n = len(boxes)
        parent = list(range(n))
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i])
            return parent[i]
        def union(i, j):
            ri, rj = find(i), find(j)
            if ri != rj: parent[ri] = rj

        for i in range(n):
            for j in range(i + 1, n):
                bi, bj = boxes[i], boxes[j]
                dx = max(0, max(bi["x1"], bj["x1"]) - min(bi["x2"], bj["x2"]))
                dy = max(0, max(bi["y1"], bj["y1"]) - min(bi["y2"], bj["y2"]))
                if dx < 65 and dy < 65:
                    union(i, j)

        clusters = {}
        for i in range(n):
            clusters.setdefault(find(i), []).append(boxes[i])

        # 過濾文字行太少的雜訊 (名片通常 >= 3 行文字)
        c_list = [c for c in clusters.values() if len(c) >= 3]

        # 幾何尺寸約束合併 (Constrained Merging)
        merged = True
        while merged:
            merged = False
            for i in range(len(c_list)):
                for j in range(i + 1, len(c_list)):
                    c1, c2 = c_list[i], c_list[j]
                    x1 = min(min(b['x1'] for b in c1), min(b['x1'] for b in c2))
                    y1 = min(min(b['y1'] for b in c1), min(b['y1'] for b in c2))
                    x2 = max(max(b['x2'] for b in c1), max(b['x2'] for b in c2))
                    y2 = max(max(b['y2'] for b in c1), max(b['y2'] for b in c2))
                    w, h = x2 - x1, y2 - y1
                    c1_x1, c1_y1 = min(b['x1'] for b in c1), min(b['y1'] for b in c1)
                    c1_x2, c1_y2 = max(b['x2'] for b in c1), max(b['y2'] for b in c1)
                    c2_x1, c2_y1 = min(b['x2'] for b in c2), min(b['y1'] for b in c2)
                    c2_x2, c2_y2 = max(b['x2'] for b in c2), max(b['y2'] for b in c2)
                    dx = max(0, max(c1_x1, c2_x1) - min(c1_x2, c2_x2))
                    dy = max(0, max(c1_y1, c2_y1) - min(c1_y2, c2_y2))
                    if w <= 750 and h <= 500 and (dx < 75 and dy < 75):
                        c_list[i] = c1 + c2
                        c_list.pop(j)
                        merged = True
                        break
                if merged: break

        sorted_clusters = sorted(c_list, key=lambda cl: (min(b['y1'] for b in cl) // 350, min(b['x1'] for b in cl)))
        print(f"  └─ 第 {page_num} 頁偵測到 {len(sorted_clusters)} 張名片")

        for c in sorted_clusters:
            card_counter += 1
            x1 = max(0, min(b['x1'] for b in c) - 20)
            y1 = max(0, min(b['y1'] for b in c) - 20)
            x2 = min(pw, max(b['x2'] for b in c) + 20)
            y2 = min(ph, max(b['y2'] for b in c) + 20)

            card_crop = page_bgr[y1:y2, x1:x2]
            card_filename = f"Card_{card_counter:03d}_P{page_num:02d}.jpg"
            card_save_path = os.path.join(cards_img_dir, card_filename)
            cv2.imencode('.jpg', card_crop)[1].tofile(card_save_path)

            card_lines = [b['text'] for b in sorted(c, key=lambda b: (b['y1']//20, b['x1']))]
            fields = parse_card_fields(card_lines)
            fields["編號"] = card_counter
            fields["來源頁碼"] = f"第 {page_num} 頁"
            fields["圖檔檔名"] = card_filename
            all_cards_data.append(fields)

    ocr.exit()

    # 輸出結構化 Excel
    excel_path = os.path.join(base_output_dir, f"{filename_no_ext}_名片名冊.xlsx")
    export_to_excel(all_cards_data, excel_path)

    print(f"\n=======================================================")
    print(f"  🎉 處理完成！")
    print(f"  [*] 本次歸檔名片總數: {len(all_cards_data)} 張")
    print(f"  [*] 裁切名片圖檔已存於: {cards_img_dir}")
    print(f"  [*] 結構化 Excel 已存於: {excel_path}")
    print(f"=======================================================\n")

def find_input_files():
    input_dirs = [
        os.path.join(BASE_DIR, "input"),
        r"D:\名片\掃描輸入",
        r"D:\scan",
        r"D:\名片"
    ]
    candidates = []
    for d in input_dirs:
        if os.path.exists(d):
            for ext in ["*.pdf", "*.jpg", "*.png", "*.jpeg"]:
                candidates.extend(glob.glob(os.path.join(d, ext)))
    candidates = [c for c in candidates if "temp_pages" not in c and "裁切名片圖檔" not in c]
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates

if __name__ == "__main__":
    base_out = os.environ.get("CARD_OUTPUT_DIR", r"D:\名片")
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        files = find_input_files()
        if not files:
            print("❌ 未找到任何 PDF/JPG 掃描檔案！請將檔案放入 input 目錄。")
            sys.exit(1)
        target_file = files[0]
        print(f"[*] 自動偵測最新掃描檔案: {target_file}")
    process_file(target_file, base_out)
