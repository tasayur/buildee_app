p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f:
    txt = f.read()

# ① ツールバーのボタンにラベルを付ける（アイコン＋テキスト）
old_toolbar = '''          <div class="tb-grp">
            <button class="sm-tool active" id="smt-select"   onclick="setMapTool('select',this)"   title="選択">🖱</button>
            <button class="sm-tool"        id="smt-pin"      onclick="setMapTool('pin',this)"      title="ピン">📍</button>
            <button class="sm-tool"        id="smt-range"    onclick="setMapTool('range',this)"    title="作業範囲">🟦</button>
            <button class="sm-tool"        id="smt-area"     onclick="setMapTool('area',this)"     title="エリア">🟥</button>
            <button class="sm-tool"        id="smt-material" onclick="setMapTool('material',this)" title="資材">📦</button>
            <button class="sm-tool"        id="smt-aerial"   onclick="setMapTool('aerial',this)"   title="高所作業">🏗️</button>
            <button class="sm-tool"        id="smt-fire"     onclick="setMapTool('fire',this)"     title="火気作業">🔥</button>
            <button class="sm-tool"        id="smt-comment"  onclick="setMapTool('comment',this)"  title="コメント">💬</button>
          </div>'''

new_toolbar = '''          <div class="tb-grp">
            <button class="sm-tool active" id="smt-select"   onclick="setMapTool('select',this)"   title="選択"><span class="tl-icon">🖱</span><span class="tl-lbl">選択</span></button>
            <button class="sm-tool"        id="smt-pin"      onclick="setMapTool('pin',this)"      title="ピン"><span class="tl-icon">📍</span><span class="tl-lbl">ピン</span></button>
            <button class="sm-tool"        id="smt-range"    onclick="setMapTool('range',this)"    title="作業範囲"><span class="tl-icon">🟦</span><span class="tl-lbl">作業範囲</span></button>
            <button class="sm-tool"        id="smt-area"     onclick="setMapTool('area',this)"     title="エリア"><span class="tl-icon">🟥</span><span class="tl-lbl">エリア</span></button>
            <button class="sm-tool"        id="smt-material" onclick="setMapTool('material',this)" title="資材"><span class="tl-icon">📦</span><span class="tl-lbl">資材</span></button>
            <button class="sm-tool"        id="smt-aerial"   onclick="setMapTool('aerial',this)"   title="高所作業"><span class="tl-icon">🏗️</span><span class="tl-lbl">高所</span></button>
            <button class="sm-tool"        id="smt-fire"     onclick="setMapTool('fire',this)"     title="火気作業"><span class="tl-icon">🔥</span><span class="tl-lbl">火気</span></button>
            <button class="sm-tool"        id="smt-comment"  onclick="setMapTool('comment',this)"  title="コメント"><span class="tl-icon">💬</span><span class="tl-lbl">メモ</span></button>
          </div>'''

txt = txt.replace(old_toolbar, new_toolbar, 1)

# ② 右パネルの「マーカー種別」パネルを削除
old_panel = '''      <!-- マーカー種別 -->
      <div class="sm-panel">
        <div class="sm-panel-hdr" style="background:#475569;"><span style="color:#fff">🗂 マーカー種別（クリックで選択）</span></div>
        <div class="mk-legend">
          <div class="ml-item" onclick="setMapTool('pin',document.getElementById('smt-pin'))">📍 ピン</div>
          <div class="ml-item" onclick="setMapTool('range',document.getElementById('smt-range'))">🟦 作業範囲</div>
          <div class="ml-item" onclick="setMapTool('area',document.getElementById('smt-area'))">🟥 エリア</div>
          <div class="ml-item" onclick="setMapTool('material',document.getElementById('smt-material'))">📦 資材</div>
          <div class="ml-item" onclick="setMapTool('aerial',document.getElementById('smt-aerial'))">🏗️ 高所作業</div>
          <div class="ml-item" onclick="setMapTool('fire',document.getElementById('smt-fire'))">🔥 火気作業</div>
          <div class="ml-item" onclick="setMapTool('comment',document.getElementById('smt-comment'))">💬 コメント</div>
        </div>
      </div>'''

txt = txt.replace(old_panel, '', 1)

# ③ ツールバーのボタンスタイルをラベル付きに変更
old_css = '''.sm-tool{padding:5px 7px;border:2px solid #e2e8f0;border-radius:5px;background:#fff;cursor:pointer;font-size:.95rem;line-height:1;transition:all .12s;}
.sm-tool:hover{border-color:#1E88E5;background:#EFF6FF;}
.sm-tool.active{border-color:#1E88E5;background:#1E88E5;}'''

new_css = '''.sm-tool{display:flex;flex-direction:column;align-items:center;gap:1px;
  padding:4px 8px;border:2px solid #e2e8f0;border-radius:6px;background:#fff;
  cursor:pointer;line-height:1;transition:all .12s;min-width:44px;}
.sm-tool:hover{border-color:#1E88E5;background:#EFF6FF;}
.sm-tool.active{border-color:#1E88E5;background:#1E88E5;color:#fff;}
.tl-icon{font-size:.95rem;}
.tl-lbl{font-size:.58rem;font-weight:bold;color:#475569;white-space:nowrap;}
.sm-tool.active .tl-lbl{color:#fff;}'''

txt = txt.replace(old_css, new_css, 1)

with open(p, 'w', encoding='utf-8') as f:
    f.write(txt)

print('OK')
