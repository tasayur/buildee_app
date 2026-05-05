import fitz, os

files = [
    (r'C:\Users\tasayur\Desktop\図面\HSG1_3F.pdf',     r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_3f.png'),
    (r'C:\Users\tasayur\Desktop\図面\HSG1_4F.pdf',     r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_4f.png'),
    (r'C:\Users\tasayur\Desktop\図面\HSG1_5F.pdf',     r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_5f.png'),
    (r'C:\Users\tasayur\Desktop\図面\HSG1_5F屋上.pdf', r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_roof.png'),
    (r'C:\Users\tasayur\Desktop\図面\HSG1_屋外.pdf',   r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_outdoor.png'),
]

for src, dst in files:
    if not os.path.exists(src):
        print(f'NOT FOUND: {src}')
        continue
    doc  = fitz.open(src)
    page = doc[0]
    mat  = fitz.Matrix(3.0, 3.0)   # 解像度3倍（約220dpi相当）
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(dst)
    sz   = os.path.getsize(dst)
    print(f'OK  {os.path.basename(dst):35s}  {sz//1024} KB')
    doc.close()

print('Done.')
