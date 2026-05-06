p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f: txt = f.read()

# ============================================================
# 1. ピン設定セクション HTML を全面置き換え
# ============================================================
old_pin_section = '''    <!-- ピン設定 -->
    <div class="pin-section">
      <div class="pin-sec-hdr">
        <span>📍 配置図ピン設定（任意）</span>
        <div style="display:flex;gap:4px;">
          <button class="pin-ftab active" id="mpt-1f"      onclick="switchModalFloor('1f',this)">1F</button>
          <button class="pin-ftab"        id="mpt-2f"      onclick="switchModalFloor('2f',this)">2F</button>
          <button class="pin-ftab"        id="mpt-3f"      onclick="switchModalFloor('3f',this)">3F</button>
          <button class="pin-ftab"        id="mpt-4f"      onclick="switchModalFloor('4f',this)">4F</button>
          <button class="pin-ftab"        id="mpt-5f"      onclick="switchModalFloor('5f',this)">5F</button>
          <button class="pin-ftab"        id="mpt-roof"    onclick="switchModalFloor('roof',this)">屋上</button>
          <button class="pin-ftab"        id="mpt-outdoor" onclick="switchModalFloor('outdoor',this)">屋外</button>
          <button class="pin-ftab clear"  onclick="clearModalPin()">✕ 削除</button>
        </div>
      </div>
      <p style="font-size:.75rem;color:#888;margin:.25rem 0 .4rem;">図面をクリックしてピンを設定</p>
      <div class="pin-map-wrap" id="modalPinWrap">
        <div id="modalPinCanvas" style="position:relative;display:inline-block;min-width:100%;">
          <img id="modalPinImg" src="/static/floorplans/floorplan_1f.png"
               draggable="false" style="display:block;width:100%;"
               onload="redrawModalPin()">
          <div id="modalPinDot" style="display:none;position:absolute;width:24px;height:24px;
            border-radius:50% 50% 50% 0;transform:rotate(-45deg) translate(-50%,-50%);
            border:3px solid rgba(255,255,255,.85);box-shadow:2px 2px 5px rgba(0,0,0,.4);
            pointer-events:none;z-index:20;background:#1E88E5;"></div>
          <div id="modalExistPins"></div>
        </div>
      </div>
      <input type="hidden" id="sch_floor"><input type="hidden" id="sch_map_x"><input type="hidden" id="sch_map_y">
      <div id="modalPinInfo" style="display:none;font-size:.78rem;color:#1E88E5;padding:.3rem .5rem;background:#E3F2FD;border-radius:4px;margin-top:.3rem;"></div>
    </div>'''

new_pin_section = '''    <!-- ===== 配置図マーカー設定（複数配置対応） ===== -->
    <div class="pin-section">
      <!-- ヘッダー：フロア選択 -->
      <div class="pin-sec-hdr">
        <span>📍 配置図マーカー設定（任意・複数配置可）</span>
      </div>
      <!-- フロアタブ -->
      <div class="mfloor-tabs">
        <button class="pin-ftab active" id="mpt-1f"      onclick="switchModalFloor('1f',this)">1F</button>
        <button class="pin-ftab"        id="mpt-2f"      onclick="switchModalFloor('2f',this)">2F</button>
        <button class="pin-ftab"        id="mpt-3f"      onclick="switchModalFloor('3f',this)">3F</button>
        <button class="pin-ftab"        id="mpt-4f"      onclick="switchModalFloor('4f',this)">4F</button>
        <button class="pin-ftab"        id="mpt-5f"      onclick="switchModalFloor('5f',this)">5F</button>
        <button class="pin-ftab"        id="mpt-roof"    onclick="switchModalFloor('roof',this)">屋上</button>
        <button class="pin-ftab"        id="mpt-outdoor" onclick="switchModalFloor('outdoor',this)">屋外</button>
      </div>
      <!-- ツール選択 -->
      <div class="mtool-bar">
        <span style="font-size:.75rem;color:#64748b;font-weight:bold;">ツール：</span>
        <button class="mtool active" id="mt-area"     onclick="setModalTool('area',this)"    title="作業エリア（ドラッグ）">🟦 作業エリア</button>
        <button class="mtool"        id="mt-pin"      onclick="setModalTool('pin',this)"     title="位置ピン">📍 ピン</button>
        <button class="mtool"        id="mt-material" onclick="setModalTool('material',this)" title="資材置き場">📦 資材</button>
        <button class="mtool"        id="mt-aerial"   onclick="setModalTool('aerial',this)"  title="高所作業">🏗️ 高所</button>
        <button class="mtool"        id="mt-fire"     onclick="setModalTool('fire',this)"    title="火気作業">🔥 火気</button>
      </div>
      <p class="mtool-hint" id="mtoolHint">🟦 図面上をドラッグして作業エリアを設定</p>
      <!-- 配置図 -->
      <div class="pin-map-wrap" id="modalPinWrap">
        <div id="modalPinCanvas" style="position:relative;display:inline-block;min-width:100%;user-select:none;">
          <img id="modalPinImg" src="/static/floorplans/floorplan_1f.png"
               draggable="false" style="display:block;width:100%;"
               onload="onModalImgLoad()">
          <!-- 他の作業予定のピン（薄く表示） -->
          <div id="modalExistPins" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
          <!-- このスケジュールのマーカー -->
          <div id="modalMarkerLayer" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></div>
          <!-- ドラッグ中プレビュー -->
          <div id="modalDragPreview" style="display:none;position:absolute;pointer-events:none;z-index:100;
            border:2px dashed #1E88E5;background:rgba(30,136,229,.12);"></div>
        </div>
      </div>
      <!-- 追加済みマーカー一覧 -->
      <div id="modalMarkerList" style="margin-top:.5rem;display:flex;flex-wrap:wrap;gap:5px;"></div>
      <!-- 旧互換用hidden（保存時は使わない） -->
      <input type="hidden" id="sch_floor" value="">
      <input type="hidden" id="sch_map_x" value="">
      <input type="hidden" id="sch_map_y" value="">
    </div>'''

txt = txt.replace(old_pin_section, new_pin_section, 1)

# ============================================================
# 2. CSS 追加（</style> の直前）
# ============================================================
old_style_end = '''.me-marker{z-index:50;}
</style>'''
new_style = '''.me-marker{z-index:50;}

/* ===== モーダルマーカーUI ===== */
.mfloor-tabs{display:flex;flex-wrap:wrap;gap:3px;margin:.4rem 0;}
.mtool-bar{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-bottom:.3rem;}
.mtool{padding:4px 9px;border:2px solid #e2e8f0;border-radius:6px;background:#fff;
  cursor:pointer;font-size:.78rem;font-weight:bold;transition:all .12s;}
.mtool:hover{border-color:#1E88E5;background:#EFF6FF;}
.mtool.active{border-color:#1E88E5;background:#1E88E5;color:#fff;}
.mtool-hint{font-size:.72rem;color:#888;margin:.1rem 0 .3rem;}
/* マーカーバッジ */
.mk-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;
  border-radius:12px;font-size:.75rem;font-weight:bold;color:#fff;cursor:default;}
.mk-badge .mk-del{background:none;border:none;color:rgba(255,255,255,.8);
  cursor:pointer;font-size:.9rem;padding:0 0 0 3px;line-height:1;}
.mk-badge .mk-del:hover{color:#fff;}
</style>'''
txt = txt.replace(old_style_end, new_style, 1)

with open(p, 'w', encoding='utf-8') as f: f.write(txt)
print('HTML/CSS OK')
