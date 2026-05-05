
# ====================================================
# Stepmap フロアタブ追加
# ====================================================
p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f: txt = f.read()

# フロアタブ（2F → 2F〜屋外）
old = '''            <button class="sm-ftab active" id="smf-1f" onclick="switchFloor('1f',this)">1F</button>
            <button class="sm-ftab"        id="smf-2f" onclick="switchFloor('2f',this)">2F</button>'''
new = '''            <button class="sm-ftab active" id="smf-1f"      onclick="switchFloor('1f',this)">1F</button>
            <button class="sm-ftab"        id="smf-2f"      onclick="switchFloor('2f',this)">2F</button>
            <button class="sm-ftab"        id="smf-3f"      onclick="switchFloor('3f',this)">3F</button>
            <button class="sm-ftab"        id="smf-4f"      onclick="switchFloor('4f',this)">4F</button>
            <button class="sm-ftab"        id="smf-5f"      onclick="switchFloor('5f',this)">5F</button>
            <button class="sm-ftab"        id="smf-roof"    onclick="switchFloor('roof',this)">屋上</button>
            <button class="sm-ftab"        id="smf-outdoor" onclick="switchFloor('outdoor',this)">屋外</button>'''
txt = txt.replace(old, new, 1)

with open(p, 'w', encoding='utf-8') as f: f.write(txt)
print('stepmap.html OK')

# ====================================================
# 配置図 (floorplan.html) フロアタブ＋パネル追加
# ====================================================
p2 = r'C:\Users\tasayur\Desktop\buildee_app\templates\floorplan.html'
with open(p2, encoding='utf-8') as f: txt2 = f.read()

# フロアタブ
old2 = '''<div class="fp-floor-tabs">
  <button class="fp-ftab active" id="fptab-1f" onclick="switchFloor('1f',this)">1F</button>
  <button class="fp-ftab"        id="fptab-2f" onclick="switchFloor('2f',this)">2F</button>
</div>'''
new2 = '''<div class="fp-floor-tabs">
  <button class="fp-ftab active" id="fptab-1f"      onclick="switchFloor('1f',this)">1F</button>
  <button class="fp-ftab"        id="fptab-2f"      onclick="switchFloor('2f',this)">2F</button>
  <button class="fp-ftab"        id="fptab-3f"      onclick="switchFloor('3f',this)">3F</button>
  <button class="fp-ftab"        id="fptab-4f"      onclick="switchFloor('4f',this)">4F</button>
  <button class="fp-ftab"        id="fptab-5f"      onclick="switchFloor('5f',this)">5F</button>
  <button class="fp-ftab"        id="fptab-roof"    onclick="switchFloor('roof',this)">屋上</button>
  <button class="fp-ftab"        id="fptab-outdoor" onclick="switchFloor('outdoor',this)">屋外</button>
</div>'''
txt2 = txt2.replace(old2, new2, 1)

# 2Fパネルの後ろに3F〜屋外パネルを追加
old3 = '''<!-- 2F -->
<div id="fp-floor-2f" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrap2f">
    <div id="fpCanvas2f" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImg2f" src="{{ url_for('static', filename='floorplans/floorplan_2f.png') }}"
           alt="2F" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePins2f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayer2f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>'''

new3 = '''<!-- 2F -->
<div id="fp-floor-2f" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrap2f">
    <div id="fpCanvas2f" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImg2f" src="{{ url_for('static', filename='floorplans/floorplan_2f.png') }}"
           alt="2F" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePins2f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayer2f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>

<!-- 3F -->
<div id="fp-floor-3f" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrap3f">
    <div id="fpCanvas3f" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImg3f" src="{{ url_for('static', filename='floorplans/floorplan_3f.png') }}"
           alt="3F" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePins3f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayer3f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>

<!-- 4F -->
<div id="fp-floor-4f" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrap4f">
    <div id="fpCanvas4f" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImg4f" src="{{ url_for('static', filename='floorplans/floorplan_4f.png') }}"
           alt="4F" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePins4f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayer4f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>

<!-- 5F -->
<div id="fp-floor-5f" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrap5f">
    <div id="fpCanvas5f" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImg5f" src="{{ url_for('static', filename='floorplans/floorplan_5f.png') }}"
           alt="5F" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePins5f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayer5f" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>

<!-- 屋上 -->
<div id="fp-floor-roof" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrapRoof">
    <div id="fpCanvasRoof" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImgRoof" src="{{ url_for('static', filename='floorplans/floorplan_roof.png') }}"
           alt="屋上" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePinsRoof" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayerRoof" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>

<!-- 屋外 -->
<div id="fp-floor-outdoor" class="fp-panel" style="display:none;">
  <div class="fp-wrap" id="fpWrapOutdoor">
    <div id="fpCanvasOutdoor" style="position:relative;display:inline-block;transform-origin:top left;transition:transform .15s;">
      <img id="fpImgOutdoor" src="{{ url_for('static', filename='floorplans/floorplan_outdoor.png') }}"
           alt="屋外" draggable="false" style="display:block;max-width:100%;">
      <div id="fpSchedulePinsOutdoor" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
      <div id="fpMarkerLayerOutdoor" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
    </div>
  </div>
</div>'''

txt2 = txt2.replace(old3, new3, 1)

# switchFloor JS を全フロア対応に更新
old_js = '''async function switchFloor(floor, btn) {
  currentFloor = floor;
  document.querySelectorAll('.fp-ftab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('fp-floor-1f').style.display = floor === '1f' ? '' : 'none';
  document.getElementById('fp-floor-2f').style.display = floor === '2f' ? '' : 'none';

  // エンジンを再初期化
  initEngine(floor);
  await engine.load(floor);
  renderSchedulePins(floor);
}'''

new_js = '''const ALL_FLOORS = ['1f','2f','3f','4f','5f','roof','outdoor'];
function floorKey(f){ return f.charAt(0).toUpperCase()+f.slice(1); }

async function switchFloor(floor, btn) {
  currentFloor = floor;
  document.querySelectorAll('.fp-ftab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  ALL_FLOORS.forEach(f => {
    const el = document.getElementById('fp-floor-'+f);
    if(el) el.style.display = f === floor ? '' : 'none';
  });
  initEngine(floor);
  await engine.load(floor);
  renderSchedulePins(floor);
}'''

txt2 = txt2.replace(old_js, new_js, 1)

# initEngine も全フロア対応（canvasId の大文字/小文字を正規化）
old_ie = '''function initEngine(floor) {
  engine = new MarkerEngine({
    canvasId: `fpCanvas${floor}`,
    imgId:    `fpImg${floor}`,
    layerId:  `fpMarkerLayer${floor}`,
    floor:    floor,
    readOnly: false,
    onSave:   () => setSyncBadge('ok', '✅ 保存しました'),
  });
}'''

new_ie = '''function floorId(f){
  // 1f -> 1f, roof -> Roof, outdoor -> Outdoor
  if(f==='roof') return 'Roof';
  if(f==='outdoor') return 'Outdoor';
  return f;
}
function initEngine(floor) {
  const fid = floorId(floor);
  engine = new MarkerEngine({
    canvasId: `fpCanvas${fid}`,
    imgId:    `fpImg${fid}`,
    layerId:  `fpMarkerLayer${fid}`,
    floor:    floor,
    readOnly: false,
    onSave:   () => setSyncBadge('ok', '✅ 保存しました'),
  });
}'''

txt2 = txt2.replace(old_ie, new_ie, 1)

# renderSchedulePins・loadSchedules も全フロア対応
old_rsp = '''  const layerId = `fpSchedulePins${floor}`;
  const layer = document.getElementById(layerId);
  if (!layer) return;
  layer.innerHTML = '';
  if (!document.getElementById('togSchedules').checked) return;

  const img = document.getElementById(`fpImg${floor}`);'''

new_rsp = '''  const fid2 = floorId(floor);
  const layerId = `fpSchedulePins${fid2}`;
  const layer = document.getElementById(layerId);
  if (!layer) return;
  layer.innerHTML = '';
  if (!document.getElementById('togSchedules').checked) return;

  const img = document.getElementById(`fpImg${fid2}`);'''

txt2 = txt2.replace(old_rsp, new_rsp, 1)

with open(p2, 'w', encoding='utf-8') as f: f.write(txt2)
print('floorplan.html OK')
print('All done.')
