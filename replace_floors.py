import fitz, os

files = [
    (r'C:\Users\tasayur\Desktop\図面\HSG1_1F.pdf',    r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_1f.png'),
    (r'C:\Users\tasayur\Desktop\図面\HSG1_屋外2.pdf', r'C:\Users\tasayur\Desktop\buildee_app\static\floorplans\floorplan_outdoor.png'),
]

for src, dst in files:
    if not os.path.exists(src):
        print(f'NOT FOUND: {src}')
        continue
    doc  = fitz.open(src)
    page = doc[0]
    pix  = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), alpha=False)
    pix.save(dst)
    sz   = os.path.getsize(dst)
    print(f'OK  {os.path.basename(dst):35s}  {sz//1024} KB')
    doc.close()

print('Done.')
