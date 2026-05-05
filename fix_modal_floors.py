p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f: txt = f.read()

# モーダルのピンフロアタブ
old = '''          <button class="pin-ftab active" id="mpt-1f" onclick="switchModalFloor('1f',this)">1F</button>
          <button class="pin-ftab"        id="mpt-2f" onclick="switchModalFloor('2f',this)">2F</button>
          <button class="pin-ftab clear"  onclick="clearModalPin()">✕ 削除</button>'''
new = '''          <button class="pin-ftab active" id="mpt-1f"      onclick="switchModalFloor('1f',this)">1F</button>
          <button class="pin-ftab"        id="mpt-2f"      onclick="switchModalFloor('2f',this)">2F</button>
          <button class="pin-ftab"        id="mpt-3f"      onclick="switchModalFloor('3f',this)">3F</button>
          <button class="pin-ftab"        id="mpt-4f"      onclick="switchModalFloor('4f',this)">4F</button>
          <button class="pin-ftab"        id="mpt-5f"      onclick="switchModalFloor('5f',this)">5F</button>
          <button class="pin-ftab"        id="mpt-roof"    onclick="switchModalFloor('roof',this)">屋上</button>
          <button class="pin-ftab"        id="mpt-outdoor" onclick="switchModalFloor('outdoor',this)">屋外</button>
          <button class="pin-ftab clear"  onclick="clearModalPin()">✕ 削除</button>'''
txt = txt.replace(old, new, 1)

# openSchModal のフロアタブ active 切替
old2 = '''  document.getElementById('mpt-1f').classList.toggle('active',modalPinFloor==='1f');
  document.getElementById('mpt-2f').classList.toggle('active',modalPinFloor==='2f');'''
new2 = '''  ['1f','2f','3f','4f','5f','roof','outdoor'].forEach(f=>{
    const b=document.getElementById('mpt-'+f);
    if(b) b.classList.toggle('active', modalPinFloor===f);
  });'''
txt = txt.replace(old2, new2, 1)

# switchModalFloor の active 切替
old3 = "  document.querySelectorAll('.pin-ftab:not(.clear)').forEach(b=>b.classList.remove('active'));"
new3 = "  document.querySelectorAll('.pin-ftab:not(.clear)').forEach(b=>b.classList.remove('active')); // all floors"
txt = txt.replace(old3, new3, 1)

with open(p, 'w', encoding='utf-8') as f: f.write(txt)
print('OK')
