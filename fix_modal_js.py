p = r'C:\Users\tasayur\Desktop\buildee_app\templates\stepmap.html'
with open(p, encoding='utf-8') as f: txt = f.read()

# ============================================================
# 旧ピン関数群を新マルチマーカー関数群に置き換え
# ============================================================
old_js = '''// ================================================================
// モーダルピン
// ================================================================
function switchModalFloor(floor,btn){
  modalPinFloor=floor;
  document.querySelectorAll('.pin-ftab:not(.clear)').forEach(b=>b.classList.remove('active')); // all floors
  btn.classList.add('active');
  document.getElementById('modalPinImg').src=`/static/floorplans/floorplan_${floor}.png`;
  document.getElementById('sch_floor').value=floor;
}
function clearModalPin(){
  modalPinX=null;modalPinY=null;
  document.getElementById('sch_floor').value='';
  document.getElementById('sch_map_x').value='';
  document.getElementById('sch_map_y').value='';
  document.getElementById('modalPinDot').style.display='none';
  document.getElementById('modalPinInfo').style.display='none';
}
function redrawModalPin(){
  const dot=document.getElementById('modalPinDot');
  const img=document.getElementById('modalPinImg');
  if(!img.naturalWidth||modalPinX===null){dot.style.display='none';return;}
  const scX=img.clientWidth/img.naturalWidth;
  const scY=img.clientHeight/img.naturalHeight;
  const color=document.getElementById('sch_color').value||'#1E88E5';
  dot.style.display='block';
  dot.style.left=(modalPinX*scX)+'px';dot.style.top=(modalPinY*scY)+'px';
  dot.style.background=color;
  const info=document.getElementById('modalPinInfo');
  info.style.display='block';
  info.textContent=`📍 ${modalPinFloor.toUpperCase()} にピン設定済み`;
}
async function loadModalExistPins(){
  const container=document.getElementById('modalExistPins');
  container.innerHTML='';
  try{
    const res=await fetch(`/api/schedules/floor/${modalPinFloor}`);
    const list=await res.json();
    const img=document.getElementById('modalPinImg');
    if(!img.naturalWidth)return;
    const scX=img.clientWidth/img.naturalWidth;
    const scY=img.clientHeight/img.naturalHeight;
    const editId=document.getElementById('sch_id').value;
    list.forEach(s=>{
      if(!s.map_x||!s.map_y||s.id===editId)return;
      const el=document.createElement('div');
      el.style.cssText=`position:absolute;width:16px;height:16px;border-radius:50% 50% 50% 0;
        transform:rotate(-45deg) translate(-50%,-50%);background:${s.color||gc(s.company)};
        opacity:.5;left:${s.map_x*scX}px;top:${s.map_y*scY}px;border:2px solid rgba(255,255,255,.7);`;
      el.title=`${s.company}：${s.work_content}`;
      container.appendChild(el);
    });
  }catch(e){}
}
// ピンクリック
document.getElementById('modalPinWrap').addEventListener('click',function(e){
  const canvas=document.getElementById('modalPinCanvas');
  const img=document.getElementById('modalPinImg');
  if(!img.naturalWidth)return;
  const rect=canvas.getBoundingClientRect();
  modalPinX=(e.clientX-rect.left)*(img.naturalWidth/img.clientWidth);
  modalPinY=(e.clientY-rect.top)*(img.naturalHeight/img.clientHeight);
  document.getElementById('sch_map_x').value=modalPinX.toFixed(1);
  document.getElementById('sch_map_y').value=modalPinY.toFixed(1);
  document.getElementById('sch_floor').value=modalPinFloor;
  redrawModalPin();
});
document.getElementById('modalPinImg').addEventListener('load',()=>{redrawModalPin();loadModalExistPins();});'''

new_js = '''// ================================================================
// モーダル マルチマーカー
// ================================================================
let modalPinFloor='1f';
let modalPinX=null, modalPinY=null; // 旧互換（未使用）
let modalTool='area';
let modalMarkers=[]; // {id,type,floor,x,y,w,h,title,color} 一時リスト
let _mdragStart=null, _mdragging=false;

const MODAL_TOOL_HINTS={
  area:'🟦 図面上をドラッグして作業エリアを囲む',
  pin:'📍 クリックして作業位置にピンを立てる',
  material:'📦 クリックして資材置き場を設定',
  aerial:'🏗️ クリックして高所作業の位置を設定',
  fire:'🔥 クリックして火気作業の位置を設定',
};
const MODAL_TOOL_COLORS={
  area:'#1E88E5', pin:'#e53935', material:'#F9A825',
  aerial:'#8E24AA', fire:'#FF6F00',
};
const MODAL_TOOL_ICONS={
  area:'🟦', pin:'📍', material:'📦', aerial:'🏗️', fire:'🔥',
};

function setModalTool(tool, btn){
  modalTool=tool;
  document.querySelectorAll('.mtool').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('mtoolHint').textContent = MODAL_TOOL_HINTS[tool]||'';
  const wrap=document.getElementById('modalPinWrap');
  wrap.style.cursor = (tool==='area') ? 'crosshair' : 'cell';
}

function switchModalFloor(floor, btn){
  modalPinFloor=floor;
  document.querySelectorAll('.pin-ftab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('modalPinImg').src=`/static/floorplans/floorplan_${floor}.png`;
}

function onModalImgLoad(){
  redrawModalMarkers();
  loadModalExistPins();
}

// ---- 座標変換 ----
function mImgCoord(clientX, clientY){
  const canvas=document.getElementById('modalPinCanvas');
  const img=document.getElementById('modalPinImg');
  if(!img.naturalWidth) return null;
  const rect=canvas.getBoundingClientRect();
  return {
    x:(clientX-rect.left)*(img.naturalWidth/img.clientWidth),
    y:(clientY-rect.top)*(img.naturalHeight/img.clientHeight)
  };
}
function mDispCoord(imgX, imgY){
  const img=document.getElementById('modalPinImg');
  if(!img.naturalWidth) return {x:0,y:0};
  return {
    x: imgX*(img.clientWidth/img.naturalWidth),
    y: imgY*(img.clientHeight/img.naturalHeight)
  };
}

// ---- マウスイベント ----
(function(){
  const wrap=document.getElementById('modalPinWrap');

  wrap.addEventListener('mousedown', e=>{
    if(modalTool!=='area') return;
    _mdragStart=mImgCoord(e.clientX,e.clientY);
    _mdragging=false;
  });

  wrap.addEventListener('mousemove', e=>{
    if(!_mdragStart) return;
    _mdragging=true;
    const cur=mImgCoord(e.clientX,e.clientY);
    if(!cur) return;
    const img=document.getElementById('modalPinImg');
    const scX=img.clientWidth/img.naturalWidth;
    const scY=img.clientHeight/img.naturalHeight;
    const x1=Math.min(_mdragStart.x,cur.x), y1=Math.min(_mdragStart.y,cur.y);
    const w=Math.abs(cur.x-_mdragStart.x), h=Math.abs(cur.y-_mdragStart.y);
    const prev=document.getElementById('modalDragPreview');
    prev.style.display='block';
    prev.style.left   =(x1*scX)+'px';
    prev.style.top    =(y1*scY)+'px';
    prev.style.width  =(w*scX)+'px';
    prev.style.height =(h*scY)+'px';
  });

  wrap.addEventListener('mouseup', e=>{
    const prev=document.getElementById('modalDragPreview');
    prev.style.display='none';

    if(modalTool==='area' && _mdragging && _mdragStart){
      const cur=mImgCoord(e.clientX,e.clientY);
      if(cur){
        const x=Math.min(_mdragStart.x,cur.x);
        const y=Math.min(_mdragStart.y,cur.y);
        const w=Math.abs(cur.x-_mdragStart.x);
        const h=Math.abs(cur.y-_mdragStart.y);
        if(w>8&&h>8){
          addModalMarker({type:'area',floor:modalPinFloor,x,y,w,h});
        }
      }
      _mdragStart=null; _mdragging=false;
      return;
    }
    _mdragStart=null; _mdragging=false;

    // ピン系クリック
    if(modalTool!=='area'){
      const pos=mImgCoord(e.clientX,e.clientY);
      if(!pos) return;
      addModalMarker({type:modalTool,floor:modalPinFloor,x:pos.x,y:pos.y});
    }
  });
})();

function addModalMarker(m){
  m.id = 'tmp_'+ Date.now() + Math.random().toString(36).slice(2,5);
  m.color = MODAL_TOOL_COLORS[m.type]||'#1E88E5';
  m.title = MODAL_TOOL_ICONS[m.type]||'';
  // ラベル入力（オプション）
  const label = prompt(`${MODAL_TOOL_ICONS[m.type]} ラベルを入力（スキップ可）`, m.title);
  if(label===null) return; // キャンセル
  m.title = label || MODAL_TOOL_ICONS[m.type];
  modalMarkers.push(m);
  redrawModalMarkers();
  renderModalMarkerList();
}

function removeModalMarker(id){
  modalMarkers=modalMarkers.filter(m=>m.id!==id);
  redrawModalMarkers();
  renderModalMarkerList();
}

function redrawModalMarkers(){
  const layer=document.getElementById('modalMarkerLayer');
  if(!layer) return;
  layer.innerHTML='';
  const img=document.getElementById('modalPinImg');
  if(!img||!img.naturalWidth) return;
  const scX=img.clientWidth/img.naturalWidth;
  const scY=img.clientHeight/img.naturalHeight;
  const floor=modalPinFloor;

  modalMarkers.filter(m=>m.floor===floor).forEach(m=>{
    const color=m.color||'#1E88E5';
    const el=document.createElement('div');
    el.style.position='absolute';

    if(m.type==='area'){
      el.style.left  =(m.x*scX)+'px';
      el.style.top   =(m.y*scY)+'px';
      el.style.width =(m.w*scX)+'px';
      el.style.height=(m.h*scY)+'px';
      el.style.border=`2px solid ${color}`;
      el.style.background=color+'22';
      el.style.borderRadius='3px';
      el.style.boxSizing='border-box';
      if(m.title){
        const lbl=document.createElement('div');
        lbl.style.cssText=`position:absolute;top:-18px;left:0;background:${color};
          color:#fff;font-size:.65rem;padding:1px 5px;border-radius:3px;
          white-space:nowrap;font-weight:bold;max-width:${m.w*scX}px;overflow:hidden;text-overflow:ellipsis;`;
        lbl.textContent=m.title;
        el.appendChild(lbl);
      }
    } else {
      // ピン系
      const dx=m.x*scX, dy=m.y*scY;
      el.style.left=dx+'px'; el.style.top=dy+'px';
      el.style.transform='translate(-50%,-50%)';

      if(m.type==='pin'){
        el.style.cssText += `position:absolute;left:${dx}px;top:${dy}px;
          width:22px;height:22px;border-radius:50% 50% 50% 0;
          transform:rotate(-45deg) translate(-50%,-50%);
          background:${color};border:2px solid rgba(255,255,255,.9);
          box-shadow:1px 1px 4px rgba(0,0,0,.4);`;
      } else {
        // ピクトグラム
        const icon={material:'📦',aerial:'🏗',fire:'🔥'}[m.type]||'📍';
        const size=28;
        el.innerHTML=`<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle cx="${size/2}" cy="${size/2}" r="${size/2-1}" fill="${color}" stroke="white" stroke-width="2"/>
          <text x="${size/2}" y="${size/2+5}" text-anchor="middle" font-size="14">${icon}</text>
        </svg>`;
        el.style.cssText=`position:absolute;left:${dx}px;top:${dy}px;
          transform:translate(-50%,-50%);
          filter:drop-shadow(1px 2px 3px rgba(0,0,0,.4));`;
        if(m.title && m.title!==icon){
          const lbl=document.createElement('div');
          lbl.style.cssText=`position:absolute;top:${size}px;left:50%;transform:translateX(-50%);
            background:rgba(0,0,0,.7);color:#fff;font-size:.6rem;padding:1px 4px;
            border-radius:3px;white-space:nowrap;`;
          lbl.textContent=m.title;
          el.appendChild(lbl);
        }
      }
    }
    layer.appendChild(el);
  });
}

function renderModalMarkerList(){
  const el=document.getElementById('modalMarkerList');
  if(!el) return;
  el.innerHTML='';
  if(!modalMarkers.length){
    el.innerHTML='<span style="font-size:.72rem;color:#94a3b8;">マーカーなし（図面上で追加してください）</span>';
    return;
  }
  modalMarkers.forEach(m=>{
    const badge=document.createElement('div');
    badge.className='mk-badge';
    badge.style.background=m.color||'#888';
    const floorLabel=m.floor?m.floor.toUpperCase():'';
    badge.innerHTML=`${MODAL_TOOL_ICONS[m.type]||'📍'} ${m.title||''} <small style="opacity:.7">(${floorLabel})</small>
      <button class="mk-del" onclick="removeModalMarker('${m.id}')" title="削除">✕</button>`;
    el.appendChild(badge);
  });
}

async function loadModalExistPins(){
  const container=document.getElementById('modalExistPins');
  container.innerHTML='';
  try{
    const res=await fetch(`/api/schedules/floor/${modalPinFloor}`);
    const list=await res.json();
    const img=document.getElementById('modalPinImg');
    if(!img.naturalWidth) return;
    const scX=img.clientWidth/img.naturalWidth;
    const scY=img.clientHeight/img.naturalHeight;
    const editId=document.getElementById('sch_id').value;
    list.forEach(s=>{
      if(!s.map_x||!s.map_y||s.id===editId) return;
      const el=document.createElement('div');
      el.style.cssText=`position:absolute;width:14px;height:14px;border-radius:50% 50% 50% 0;
        transform:rotate(-45deg) translate(-50%,-50%);background:${s.color||gc(s.company)};
        opacity:.4;left:${s.map_x*scX}px;top:${s.map_y*scY}px;border:2px solid rgba(255,255,255,.6);`;
      el.title=`${s.company}：${s.work_content}`;
      container.appendChild(el);
    });
  }catch(e){}
}

// ---- 登録時にAPIへ保存 ----
async function saveModalMarkers(scheduleId){
  const color=document.getElementById('sch_color').value||'#1E88E5';
  for(const m of modalMarkers){
    const data={
      id:'mk'+Date.now()+Math.random().toString(36).slice(2,5),
      floor:m.floor, type:m.type,
      x:m.x, y:m.y,
      w:m.w||null, h:m.h||null,
      color:m.color||color,
      title:m.title||'',
      body:scheduleId||'',
    };
    await fetch('/api/markers',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(data)
    });
  }
}

// ---- モーダルを開いたときに既存マーカーを読み込む ----
async function loadExistingModalMarkers(scheduleId){
  modalMarkers=[];
  if(!scheduleId) return;
  // bodyフィールドにscheduleIdを入れて保存しているので検索
  try{
    const res=await fetch('/api/markers');
    const all=await res.json();
    const mine=all.filter(m=>m.body===scheduleId);
    mine.forEach(m=>{
      modalMarkers.push({
        id:m.id, type:m.type, floor:m.floor,
        x:m.x, y:m.y, w:m.w, h:m.h,
        color:m.color, title:m.title,
        _saved:true
      });
    });
  }catch(e){}
  renderModalMarkerList();
  redrawModalMarkers();
}

// ---- 削除（API保存済みのもの） ----
const _origRemoveModalMarker=window.removeModalMarker;
window.removeModalMarker=async function(id){
  const m=modalMarkers.find(x=>x.id===id);
  if(m&&m._saved){
    await fetch(`/api/markers/${id}`,{method:'DELETE'});
  }
  modalMarkers=modalMarkers.filter(x=>x.id!==id);
  redrawModalMarkers();
  renderModalMarkerList();
};'''

# ============================================================
# openSchModal に既存マーカー読み込みを追加
# ============================================================
old_open_end = '''  document.getElementById('schModal').classList.add('open');
  redrawModalPin();
  loadModalExistPins();
}'''

new_open_end = '''  // マーカーリセット
  modalMarkers=[];
  renderModalMarkerList&&renderModalMarkerList();
  document.getElementById('schModal').classList.add('open');
  // 既存マーカーを読み込む（編集時）
  const sid=document.getElementById('sch_id').value;
  if(sid){ loadExistingModalMarkers(sid); }
  else { redrawModalMarkers&&redrawModalMarkers(); }
  loadModalExistPins();
}'''

txt = txt.replace(old_open_end, new_open_end, 1)

# ============================================================
# saveSchedule に saveModalMarkers を追加
# ============================================================
old_save = '''    showToast(id?'更新しました':'登録しました','success');
    closeModal('schModal');
    loadDay(selectedDate);
  }catch(e){showToast('保存に失敗しました','error');}
}'''

new_save = '''    showToast(id?'更新しました':'登録しました','success');
    // 新規の場合はレスポンスからIDを取得してマーカーを保存
    if(!id && modalMarkers.length>0){
      // 最新のスケジュールIDを取得して紐付け
      try{
        const schRes=await fetch(`/api/schedules?date=${body.date}`);
        const schList=await schRes.json();
        // 最後に登録したもの（最新）
        const latest=schList.filter(s=>s.company===body.company&&s.work_content===body.work_content).pop();
        if(latest) await saveModalMarkers(latest.id);
      }catch(e2){}
    } else if(id && modalMarkers.length>0){
      const unsaved=modalMarkers.filter(m=>!m._saved);
      if(unsaved.length>0) await saveModalMarkers(id);
    }
    closeModal('schModal');
    loadDay(selectedDate);
    if(engine) engine.load(currentFloor);
  }catch(e){showToast('保存に失敗しました','error');}
}'''

txt = txt.replace(old_save, new_save, 1)

# ============================================================
# 旧ピン関数群を新関数群で置き換え
# ============================================================
# 既存の旧関数をnewで置換
if old_js in txt:
    txt = txt.replace(old_js, new_js, 1)
    print('JS replace: OK')
else:
    print('JS replace: OLD NOT FOUND - appending')
    # </script>の直前に追加
    txt = txt.replace('// ================================================================\n// 共通\n// ================================================================\nfunction closeModal', new_js+'\n// ================================================================\n// 共通\n// ================================================================\nfunction closeModal', 1)

with open(p, 'w', encoding='utf-8') as f: f.write(txt)
print('JS OK')
