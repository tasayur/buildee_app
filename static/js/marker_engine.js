/**
 * marker_engine.js — BuildeeMgr 共有マーカーエンジン
 * Stepmap / 配置図 / 入力ページ で共通利用
 */

// ================================================================
//  マーカー種別定義
// ================================================================
const MARKER_DEFS = {
  pin:      { icon:'📍', label:'ピン',       color:'#e53935', shape:'pin'    },
  range:    { icon:'🟦', label:'作業範囲',   color:'#1E88E5', shape:'area'   },
  material: { icon:'📦', label:'資材',       color:'#F9A825', shape:'pin'    },
  aerial:   { icon:'🏗️', label:'高所作業',   color:'#8E24AA', shape:'pin'    },
  fire:     { icon:'🔥', label:'火気作業',   color:'#FF6F00', shape:'pin'    },
  comment:  { icon:'💬', label:'コメント',   color:'#43A047', shape:'memo'   },
  memo:     { icon:'📝', label:'メモ',       color:'#F9A825', shape:'memo'   },
  area:     { icon:'🟥', label:'エリア',     color:'#e53935', shape:'area'   },
};

// ================================================================
//  ピクトグラム SVG
// ================================================================
const PICTOS = {
  pin: (color) => `<svg width="28" height="36" viewBox="0 0 28 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 0C6.27 0 0 6.27 0 14c0 9.33 14 22 14 22S28 23.33 28 14C28 6.27 21.73 0 14 0z" fill="${color}"/>
    <circle cx="14" cy="14" r="6" fill="white" opacity="0.8"/>
  </svg>`,

  material: (color) => `<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="4" fill="${color}"/>
    <text x="16" y="22" text-anchor="middle" font-size="18" fill="white">📦</text>
  </svg>`,

  aerial: (color) => `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
    <rect width="36" height="36" rx="6" fill="${color}"/>
    <text x="18" y="26" text-anchor="middle" font-size="20" fill="white">🏗</text>
  </svg>`,

  fire: (color) => `<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
    <circle cx="18" cy="18" r="17" fill="${color}" stroke="white" stroke-width="2"/>
    <text x="18" y="26" text-anchor="middle" font-size="20" fill="white">🔥</text>
  </svg>`,

  comment: (color) => `<svg width="36" height="32" viewBox="0 0 36 32" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="0" width="36" height="26" rx="6" fill="${color}"/>
    <polygon points="8,26 16,32 16,26" fill="${color}"/>
    <text x="18" y="18" text-anchor="middle" font-size="11" fill="white" font-weight="bold" font-family="sans-serif" id="ct"></text>
  </svg>`,
};

// ================================================================
//  MarkerEngine クラス
// ================================================================
class MarkerEngine {
  constructor(opts = {}) {
    this.canvasId    = opts.canvasId    || 'markerCanvas';
    this.imgId       = opts.imgId       || 'mapImg';
    this.layerId     = opts.layerId     || 'markerLayer';
    this.floor       = opts.floor       || '1f';
    this.scale       = 1.0;
    this.activeTool  = 'select';
    this.activeType  = 'pin';
    this.activeColor = null; // null = use type default
    this.markers     = [];
    this.onSave      = opts.onSave      || null;
    this.readOnly    = opts.readOnly    || false;
    this.showSchedulePins = opts.showSchedulePins !== false;

    // エリア描画用
    this._drawing  = false;
    this._drawEl   = null;
    this._drawStart= null;

    // ポップアップ
    this._popup    = null;
    this._popupMid = null;

    this._init();
  }

  // ----------------------------------------------------------------
  // 初期化
  // ----------------------------------------------------------------
  _init() {
    const canvas = document.getElementById(this.canvasId);
    if (!canvas) return;

    // クリックイベント
    const wrap = canvas.parentElement;
    wrap.addEventListener('mousedown', (e) => this._onMouseDown(e, wrap));
    wrap.addEventListener('mousemove', (e) => this._onMouseMove(e));
    wrap.addEventListener('mouseup',   (e) => this._onMouseUp(e, wrap));

    // 画像ロード後に再描画
    const img = document.getElementById(this.imgId);
    if (img) img.addEventListener('load', () => this.redraw());

    // ポップアップ作成
    this._createPopup();
  }

  // ----------------------------------------------------------------
  // ツール設定
  // ----------------------------------------------------------------
  setTool(tool) { this.activeTool = tool; }
  setType(type) { this.activeType  = type; }
  setColor(c)   { this.activeColor = c; }
  setFloor(f)   {
    this.floor = f;
    const img = document.getElementById(this.imgId);
    if (img) img.src = `/static/floorplans/floorplan_${f}.png`;
  }
  setScale(s) {
    this.scale = s;
    const canvas = document.getElementById(this.canvasId);
    if (canvas) canvas.style.transform = `scale(${s})`;
    this.redraw();
  }
  zoom(f) { this.setScale(Math.min(Math.max(this.scale * f, 0.3), 6)); }
  zoomReset() { this.setScale(1.0); }

  // ----------------------------------------------------------------
  // 座標変換（クリック座標→画像座標）
  // ----------------------------------------------------------------
  _clientToImg(clientX, clientY) {
    const canvas = document.getElementById(this.canvasId);
    const img    = document.getElementById(this.imgId);
    if (!img || !img.naturalWidth) return null;
    const rect = canvas.getBoundingClientRect();
    const dispX = clientX - rect.left;
    const dispY = clientY - rect.top;
    const scX = img.naturalWidth  / (img.clientWidth  * this.scale);
    const scY = img.naturalHeight / (img.clientHeight * this.scale);
    return { x: dispX * scX, y: dispY * scY };
  }

  // 画像座標→表示座標
  _imgToDisp(imgX, imgY) {
    const img = document.getElementById(this.imgId);
    if (!img || !img.naturalWidth) return { x: 0, y: 0 };
    const scX = (img.clientWidth  * this.scale) / img.naturalWidth;
    const scY = (img.clientHeight * this.scale) / img.naturalHeight;
    return { x: imgX * scX, y: imgY * scY };
  }

  // ----------------------------------------------------------------
  // マウスイベント
  // ----------------------------------------------------------------
  _onMouseDown(e, wrap) {
    if (this.readOnly) return;
    if (e.target.closest('.me-marker')) return; // マーカーのクリックは別処理
    if (this.activeTool === 'select') return;

    const def = MARKER_DEFS[this.activeType] || MARKER_DEFS.pin;

    if (def.shape === 'area') {
      // エリア描画開始
      this._drawing   = true;
      const pos = this._clientToImg(e.clientX, e.clientY);
      this._drawStart = pos;
      const canvas = document.getElementById(this.canvasId);
      this._drawEl = document.createElement('div');
      this._drawEl.style.cssText = `position:absolute;border:2px dashed ${this._getColor()};
        background:${this._getColor()}22;pointer-events:none;z-index:200;`;
      canvas.appendChild(this._drawEl);
    }
  }

  _onMouseMove(e) {
    if (!this._drawing || !this._drawEl) return;
    const pos = this._clientToImg(e.clientX, e.clientY);
    if (!pos) return;
    const x = Math.min(pos.x, this._drawStart.x);
    const y = Math.min(pos.y, this._drawStart.y);
    const w = Math.abs(pos.x - this._drawStart.x);
    const h = Math.abs(pos.y - this._drawStart.y);
    const d = this._imgToDisp(x, y);
    const dw = w * (document.getElementById(this.imgId).clientWidth * this.scale) / document.getElementById(this.imgId).naturalWidth;
    const dh = h * (document.getElementById(this.imgId).clientHeight * this.scale) / document.getElementById(this.imgId).naturalHeight;
    this._drawEl.style.left   = d.x + 'px';
    this._drawEl.style.top    = d.y + 'px';
    this._drawEl.style.width  = dw + 'px';
    this._drawEl.style.height = dh + 'px';
  }

  _onMouseUp(e, wrap) {
    if (this.readOnly) return;
    if (this._drawing) {
      this._drawing = false;
      const canvas = document.getElementById(this.canvasId);
      if (this._drawEl) { canvas.removeChild(this._drawEl); this._drawEl = null; }

      const pos = this._clientToImg(e.clientX, e.clientY);
      if (!pos) return;
      const x = Math.min(pos.x, this._drawStart.x);
      const y = Math.min(pos.y, this._drawStart.y);
      const w = Math.abs(pos.x - this._drawStart.x);
      const h = Math.abs(pos.y - this._drawStart.y);
      if (w < 10 || h < 10) return;
      this._openLabelDialog({
        type: this.activeType, floor: this.floor,
        x, y, w, h, color: this._getColor()
      });
    }
    // ピン系
    else if (this.activeTool !== 'select') {
      if (e.target.closest('.me-marker')) return;
      const def = MARKER_DEFS[this.activeType] || MARKER_DEFS.pin;
      if (def.shape !== 'area') {
        const pos = this._clientToImg(e.clientX, e.clientY);
        if (!pos) return;
        const needsLabel = ['comment','memo','aerial','fire','material'].includes(this.activeType);
        if (needsLabel) {
          this._openLabelDialog({
            type: this.activeType, floor: this.floor,
            x: pos.x, y: pos.y, color: this._getColor()
          });
        } else {
          this._saveMarker({
            type: this.activeType, floor: this.floor,
            x: pos.x, y: pos.y, color: this._getColor(),
            title: MARKER_DEFS[this.activeType]?.label || 'ピン', body: ''
          });
        }
      }
    }
  }

  _getColor() {
    return this.activeColor || MARKER_DEFS[this.activeType]?.color || '#e53935';
  }

  // ----------------------------------------------------------------
  // ラベル入力ダイアログ
  // ----------------------------------------------------------------
  _openLabelDialog(data) {
    // 既存ダイアログを削除
    document.getElementById('me-label-dialog')?.remove();

    const def = MARKER_DEFS[data.type] || MARKER_DEFS.pin;
    const needsBody = ['comment','memo','aerial','fire'].includes(data.type);

    const dlg = document.createElement('div');
    dlg.id = 'me-label-dialog';
    dlg.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,.5);
      z-index:9000;display:flex;align-items:center;justify-content:center;`;
    dlg.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:1.5rem;width:320px;
        box-shadow:0 8px 32px rgba(0,0,0,.25);">
        <h3 style="margin:0 0 1rem;display:flex;align-items:center;gap:8px;">
          <span>${def.icon}</span> ${def.label} を追加
        </h3>
        <label style="font-size:.8rem;font-weight:bold;color:#475569">タイトル</label>
        <input id="me-dlg-title" type="text" placeholder="${def.label}" maxlength="40"
          style="width:100%;border:1px solid #ccc;border-radius:6px;padding:.45rem .65rem;
          font-size:.9rem;box-sizing:border-box;margin:.3rem 0 .75rem;">
        ${needsBody ? `
        <label style="font-size:.8rem;font-weight:bold;color:#475569">メモ</label>
        <textarea id="me-dlg-body" rows="3" maxlength="200" placeholder="詳細メモ"
          style="width:100%;border:1px solid #ccc;border-radius:6px;padding:.45rem .65rem;
          font-size:.9rem;box-sizing:border-box;margin:.3rem 0 .75rem;font-family:inherit;resize:vertical;"></textarea>
        ` : ''}
        <div style="display:flex;gap:.5rem;justify-content:flex-end;">
          <button id="me-dlg-cancel" style="padding:.4rem 1.2rem;border:1px solid #ccc;
            border-radius:6px;background:#fff;cursor:pointer;">キャンセル</button>
          <button id="me-dlg-ok" style="padding:.4rem 1.5rem;background:#1E88E5;color:#fff;
            border:none;border-radius:6px;cursor:pointer;font-weight:bold;">追加</button>
        </div>
      </div>`;
    document.body.appendChild(dlg);

    setTimeout(() => document.getElementById('me-dlg-title').focus(), 50);

    document.getElementById('me-dlg-cancel').onclick = () => dlg.remove();
    document.getElementById('me-dlg-ok').onclick = () => {
      const title = document.getElementById('me-dlg-title').value.trim() || def.label;
      const body  = document.getElementById('me-dlg-body')?.value.trim() || '';
      dlg.remove();
      this._saveMarker({ ...data, title, body });
    };
    dlg.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) document.getElementById('me-dlg-ok')?.click();
      if (e.key === 'Escape') dlg.remove();
    });
  }

  // ----------------------------------------------------------------
  // マーカー保存（API→再描画）
  // ----------------------------------------------------------------
  async _saveMarker(data) {
    data.id = 'mk' + Date.now() + Math.random().toString(36).slice(2, 6);
    try {
      const res = await fetch('/api/markers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(res.status);
      this.markers.push(data);
      this.redraw();
      if (this.onSave) this.onSave(data);
    } catch(e) { console.error('marker save error', e); }
  }

  // ----------------------------------------------------------------
  // マーカー削除
  // ----------------------------------------------------------------
  async deleteMarker(id) {
    try {
      await fetch(`/api/markers/${id}`, { method: 'DELETE' });
      this.markers = this.markers.filter(m => m.id !== id);
      this.redraw();
      this._closePopup();
    } catch(e) { console.error('marker delete error', e); }
  }

  // マーカー移動（ドラッグ後のPUT）
  async moveMarker(id, x, y) {
    try {
      await fetch(`/api/markers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x, y })
      });
      const m = this.markers.find(m => m.id === id);
      if (m) { m.x = x; m.y = y; }
    } catch(e) {}
  }

  // ----------------------------------------------------------------
  // APIからマーカーを読み込み
  // ----------------------------------------------------------------
  async load(floor) {
    if (floor) this.floor = floor;
    try {
      const res = await fetch(`/api/markers?floor=${this.floor}`);
      this.markers = await res.json();
      this.redraw();
    } catch(e) { console.error('marker load error', e); }
  }

  // ----------------------------------------------------------------
  // 全消去
  // ----------------------------------------------------------------
  async clearAll() {
    try {
      await fetch(`/api/markers/floor/${this.floor}`, { method: 'DELETE' });
      this.markers = [];
      this.redraw();
    } catch(e) {}
  }

  // ----------------------------------------------------------------
  // 再描画（全マーカー）
  // ----------------------------------------------------------------
  redraw() {
    const layer = document.getElementById(this.layerId);
    if (!layer) return;
    layer.innerHTML = '';

    this.markers.filter(m => m.floor === this.floor).forEach(m => {
      const el = this._createMarkerEl(m);
      if (el) layer.appendChild(el);
    });
  }

  // ----------------------------------------------------------------
  // マーカー要素生成
  // ----------------------------------------------------------------
  _createMarkerEl(m) {
    const def   = MARKER_DEFS[m.type] || MARKER_DEFS.pin;
    const color = m.color || def.color;
    const disp  = this._imgToDisp(m.x, m.y);
    const img   = document.getElementById(this.imgId);
    if (!img || !img.naturalWidth) return null;

    const wrap = document.createElement('div');
    wrap.className = 'me-marker';
    wrap.setAttribute('data-mid', m.id);
    wrap.style.cssText = `position:absolute;pointer-events:all;cursor:${this.readOnly?'default':'pointer'};z-index:50;`;

    if (def.shape === 'area') {
      // エリア・作業範囲
      const scX = (img.clientWidth  * this.scale) / img.naturalWidth;
      const scY = (img.clientHeight * this.scale) / img.naturalHeight;
      const dw = (m.w || 80) * scX;
      const dh = (m.h || 50) * scY;
      wrap.style.left   = disp.x + 'px';
      wrap.style.top    = disp.y + 'px';
      wrap.style.width  = dw + 'px';
      wrap.style.height = dh + 'px';
      wrap.style.border = `3px ${m.type==='range'?'solid':'dashed'} ${color}`;
      wrap.style.background = color + '18';
      wrap.style.borderRadius = '4px';
      wrap.style.boxSizing = 'border-box';
      if (m.title) {
        const label = document.createElement('div');
        label.style.cssText = `position:absolute;top:-22px;left:0;background:${color};
          color:#fff;font-size:.7rem;padding:2px 6px;border-radius:4px;
          white-space:nowrap;font-weight:bold;max-width:${dw}px;overflow:hidden;text-overflow:ellipsis;`;
        label.textContent = `${def.icon} ${m.title}`;
        wrap.appendChild(label);
      }
    } else if (def.shape === 'memo') {
      // コメント・メモ
      wrap.style.left = disp.x + 'px';
      wrap.style.top  = disp.y + 'px';
      wrap.style.transform = 'translate(-50%, -100%)';
      const bubble = document.createElement('div');
      bubble.style.cssText = `background:${color};color:#fff;padding:4px 8px;
        border-radius:8px 8px 8px 0;font-size:.75rem;font-weight:bold;
        max-width:140px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        box-shadow:2px 2px 6px rgba(0,0,0,.3);`;
      bubble.textContent = `${def.icon} ${m.title || def.label}`;
      wrap.appendChild(bubble);
    } else {
      // ピン系（pin, material, aerial, fire）
      wrap.style.left = disp.x + 'px';
      wrap.style.top  = disp.y + 'px';

      if (m.type === 'aerial' || m.type === 'fire' || m.type === 'material') {
        // ピクトグラム
        const picto = document.createElement('div');
        picto.style.cssText = `transform:translate(-50%,-50%);
          filter:drop-shadow(2px 2px 3px rgba(0,0,0,.4));`;
        picto.innerHTML = this._getPicto(m.type, color);
        wrap.appendChild(picto);
        if (m.title && m.title !== def.label) {
          const lbl = document.createElement('div');
          lbl.style.cssText = `position:absolute;top:20px;left:50%;transform:translateX(-50%);
            background:rgba(0,0,0,.7);color:#fff;font-size:.65rem;padding:1px 5px;
            border-radius:3px;white-space:nowrap;`;
          lbl.textContent = m.title;
          wrap.appendChild(lbl);
        }
      } else {
        // 通常ピン
        const dot = document.createElement('div');
        dot.style.cssText = `width:26px;height:26px;border-radius:50% 50% 50% 0;
          transform:rotate(-45deg) translate(-50%,-50%);
          background:${color};border:3px solid rgba(255,255,255,.85);
          box-shadow:2px 2px 5px rgba(0,0,0,.4);`;
        wrap.appendChild(dot);
        if (m.title) {
          const lbl = document.createElement('div');
          lbl.style.cssText = `position:absolute;top:-28px;left:8px;
            background:rgba(0,0,0,.75);color:#fff;font-size:.7rem;
            padding:2px 6px;border-radius:4px;white-space:nowrap;
            pointer-events:none;opacity:0;transition:opacity .15s;`;
          lbl.textContent = m.title;
          wrap.appendChild(lbl);
          wrap.addEventListener('mouseenter', () => lbl.style.opacity='1');
          wrap.addEventListener('mouseleave', () => lbl.style.opacity='0');
        }
      }
    }

    // クリックでポップアップ
    wrap.addEventListener('click', (e) => {
      e.stopPropagation();
      if (this.activeTool !== 'select' && !this.readOnly) return;
      this._showPopup(m, e.clientX, e.clientY);
    });

    // ドラッグ移動（selectモード・readOnly以外）
    if (!this.readOnly && def.shape !== 'area') {
      this._attachDrag(wrap, m);
    }

    return wrap;
  }

  _getPicto(type, color) {
    const size = 36;
    const icons = { aerial:'🏗', fire:'🔥', material:'📦' };
    const icon = icons[type] || '📍';
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <circle cx="${size/2}" cy="${size/2}" r="${size/2-1}" fill="${color}" stroke="white" stroke-width="2.5"/>
      <text x="${size/2}" y="${size/2+7}" text-anchor="middle" font-size="18">${icon}</text>
    </svg>`;
  }

  // ----------------------------------------------------------------
  // ドラッグ
  // ----------------------------------------------------------------
  _attachDrag(el, m) {
    let dragging = false, startCX, startCY, origX, origY;
    el.addEventListener('mousedown', (e) => {
      if (this.activeTool !== 'select') return;
      e.stopPropagation();
      dragging = false;
      startCX = e.clientX; startCY = e.clientY;
      origX = m.x; origY = m.y;
      el.style.opacity = '.7';

      const onMove = (ev) => {
        const dx = ev.clientX - startCX;
        const dy = ev.clientY - startCY;
        if (Math.abs(dx)>3 || Math.abs(dy)>3) dragging = true;
        if (dragging) {
          const img = document.getElementById(this.imgId);
          const scX = (img.clientWidth  * this.scale) / img.naturalWidth;
          const scY = (img.clientHeight * this.scale) / img.naturalHeight;
          m.x = origX + dx / scX;
          m.y = origY + dy / scY;
          const d = this._imgToDisp(m.x, m.y);
          el.style.left = d.x + 'px';
          el.style.top  = d.y + 'px';
        }
      };
      const onUp = () => {
        el.style.opacity = '1';
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        if (dragging) this.moveMarker(m.id, m.x, m.y);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  // ----------------------------------------------------------------
  // ポップアップ
  // ----------------------------------------------------------------
  _createPopup() {
    document.getElementById('me-popup')?.remove();
    const pop = document.createElement('div');
    pop.id = 'me-popup';
    pop.style.cssText = `position:fixed;z-index:1000;background:#fff;border:1px solid #ddd;
      border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.2);width:260px;
      font-size:.9rem;display:none;`;
    pop.innerHTML = `
      <div id="me-pop-header" style="padding:.5rem .75rem;border-radius:10px 10px 0 0;
        display:flex;justify-content:space-between;align-items:center;color:#fff;font-weight:bold;">
        <span id="me-pop-title" style="font-size:.9rem;"></span>
        <button onclick="document.getElementById('me-popup').style.display='none'"
          style="background:none;border:none;color:#fff;cursor:pointer;font-size:1.1rem;">✕</button>
      </div>
      <div id="me-pop-body" style="padding:.75rem;color:#333;white-space:pre-wrap;min-height:30px;font-size:.85rem;"></div>
      <div id="me-pop-meta" style="padding:0 .75rem .5rem;font-size:.72rem;color:#94a3b8;"></div>
      <div id="me-pop-footer" style="padding:.5rem .75rem;border-top:1px solid #f1f5f9;
        display:flex;justify-content:flex-end;gap:6px;">
        <button id="me-pop-del" style="padding:.3rem .75rem;background:#e53935;color:#fff;
          border:none;border-radius:4px;cursor:pointer;font-size:.8rem;">🗑 削除</button>
      </div>`;
    document.body.appendChild(pop);
    this._popup = pop;

    // 外クリックで閉じる
    document.addEventListener('click', (e) => {
      if (pop.style.display !== 'none' && !pop.contains(e.target)) pop.style.display = 'none';
    });
  }

  _showPopup(m, cx, cy) {
    const def = MARKER_DEFS[m.type] || MARKER_DEFS.pin;
    const color = m.color || def.color;
    const pop = document.getElementById('me-popup');
    if (!pop) return;
    document.getElementById('me-pop-header').style.background = color;
    document.getElementById('me-pop-title').textContent  = `${def.icon} ${m.title || def.label}`;
    document.getElementById('me-pop-body').textContent   = m.body || '';
    document.getElementById('me-pop-meta').textContent   =
      `${m.created_by ? m.created_by + ' ・ ' : ''}${(m.created_at||'').slice(0,16)}`;

    const delBtn = document.getElementById('me-pop-del');
    delBtn.style.display = this.readOnly ? 'none' : 'inline-block';
    delBtn.onclick = () => this.deleteMarker(m.id);

    pop.style.display = 'block';
    this._popupMid = m.id;
    const vw = window.innerWidth, vh = window.innerHeight;
    let px = cx + 10, py = cy + 10;
    if (px + 270 > vw) px = cx - 275;
    if (py + 200 > vh) py = cy - 200;
    pop.style.left = px + 'px';
    pop.style.top  = py + 'px';
  }

  _closePopup() {
    const pop = document.getElementById('me-popup');
    if (pop) pop.style.display = 'none';
  }
}
