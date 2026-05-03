"""
図面PDF → PNG変換 & アプリのstaticフォルダに配置
"""
import fitz  # PyMuPDF
import os, shutil

PDFS = [
    (r"C:\Users\tasayur\Desktop\図面\HSG1_1F.pdf",  "floorplan_1f.png", "1F"),
    (r"C:\Users\tasayur\Desktop\図面\HSG1_2F2.pdf", "floorplan_2f.png", "2F"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "static", "floorplans")
os.makedirs(OUT_DIR, exist_ok=True)

for pdf_path, out_name, label in PDFS:
    doc = fitz.open(pdf_path)
    page = doc[0]
    # 高解像度で変換（150dpi相当）
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    out_path = os.path.join(OUT_DIR, out_name)
    pix.save(out_path)
    size_kb = os.path.getsize(out_path) // 1024
    print(f"✅ {label}: {out_name} ({size_kb} KB) → {out_path}")
    doc.close()

print("\n完了! static/floorplans/ に保存しました。")
