p = r'C:\Users\tasayur\Desktop\buildee_app\static\js\marker_engine.js'
with open(p, encoding='utf-8') as f:
    txt = f.read()

# ポップアップHTML：編集ボタンを追加
old_popup = '''    pop.innerHTML = `
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
      </div>`;'''

new_popup = '''    pop.innerHTML = `
      <div id="me-pop-header" style="padding:.5rem .75rem;border-radius:10px 10px 0 0;
        display:flex;justify-content:space-between;align-items:center;color:#fff;font-weight:bold;">
        <span id="me-pop-title" style="font-size:.9rem;flex:1;"></span>
        <button onclick="document.getElementById('me-popup').style.display='none'"
          style="background:none;border:none;color:#fff;cursor:pointer;font-size:1.1rem;margin-left:6px;">✕</button>
      </div>
      <!-- 表示モード -->
      <div id="me-pop-view">
        <div id="me-pop-body" style="padding:.65rem .75rem;color:#333;white-space:pre-wrap;font-size:.85rem;min-height:24px;"></div>
        <div id="me-pop-meta" style="padding:0 .75rem .4rem;font-size:.7rem;color:#94a3b8;"></div>
        <div style="padding:.45rem .75rem;border-top:1px solid #f1f5f9;display:flex;justify-content:flex-end;gap:6px;">
          <button id="me-pop-edit" style="padding:.3rem .75rem;background:#1E88E5;color:#fff;
            border:none;border-radius:4px;cursor:pointer;font-size:.8rem;">✏️ 編集</button>
          <button id="me-pop-del" style="padding:.3rem .75rem;background:#e53935;color:#fff;
            border:none;border-radius:4px;cursor:pointer;font-size:.8rem;">🗑 削除</button>
        </div>
      </div>
      <!-- 編集モード -->
      <div id="me-pop-edit-form" style="display:none;padding:.65rem .75rem;">
        <label style="font-size:.75rem;font-weight:bold;color:#475569;display:block;margin-bottom:3px;">タイトル</label>
        <input id="me-pop-edit-title" type="text" maxlength="60"
          style="width:100%;border:1px solid #cbd5e1;border-radius:5px;padding:.35rem .55rem;font-size:.88rem;box-sizing:border-box;margin-bottom:.5rem;">
        <label style="font-size:.75rem;font-weight:bold;color:#475569;display:block;margin-bottom:3px;">メモ</label>
        <textarea id="me-pop-edit-body" rows="3" maxlength="200"
          style="width:100%;border:1px solid #cbd5e1;border-radius:5px;padding:.35rem .55rem;font-size:.85rem;box-sizing:border-box;resize:vertical;font-family:inherit;"></textarea>
        <div style="display:flex;justify-content:flex-end;gap:6px;margin-top:.5rem;">
          <button id="me-pop-cancel-edit" style="padding:.3rem .85rem;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer;font-size:.8rem;">キャンセル</button>
          <button id="me-pop-save-edit"   style="padding:.3rem .85rem;background:#43A047;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:.8rem;font-weight:bold;">💾 保存</button>
        </div>
      </div>
    `;'''

txt = txt.replace(old_popup, new_popup, 1)

# _showPopup に編集ボタンのロジックを追加
old_show = '''    const delBtn = document.getElementById('me-pop-del');
    delBtn.style.display = this.readOnly ? 'none' : 'inline-block';
    delBtn.onclick = () => this.deleteMarker(m.id);'''

new_show = '''    // 表示モードに戻す
    document.getElementById('me-pop-view').style.display = 'block';
    document.getElementById('me-pop-edit-form').style.display = 'none';

    const delBtn = document.getElementById('me-pop-del');
    const editBtn = document.getElementById('me-pop-edit');
    const cancelBtn = document.getElementById('me-pop-cancel-edit');
    const saveBtn = document.getElementById('me-pop-save-edit');

    delBtn.style.display = this.readOnly ? 'none' : 'inline-block';
    editBtn.style.display = this.readOnly ? 'none' : 'inline-block';

    delBtn.onclick = () => this.deleteMarker(m.id);

    editBtn.onclick = () => {
      document.getElementById('me-pop-view').style.display = 'none';
      document.getElementById('me-pop-edit-form').style.display = 'block';
      document.getElementById('me-pop-edit-title').value = m.title || '';
      document.getElementById('me-pop-edit-body').value = m.body || '';
      setTimeout(() => document.getElementById('me-pop-edit-title').focus(), 50);
    };

    cancelBtn.onclick = () => {
      document.getElementById('me-pop-view').style.display = 'block';
      document.getElementById('me-pop-edit-form').style.display = 'none';
    };

    saveBtn.onclick = async () => {
      const newTitle = document.getElementById('me-pop-edit-title').value.trim();
      const newBody  = document.getElementById('me-pop-edit-body').value.trim();
      try {
        await fetch(`/api/markers/${m.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle, body: newBody })
        });
        m.title = newTitle; m.body = newBody;
        document.getElementById('me-pop-title').textContent = `${def.icon} ${newTitle || def.label}`;
        document.getElementById('me-pop-body').textContent  = newBody;
        document.getElementById('me-pop-view').style.display = 'block';
        document.getElementById('me-pop-edit-form').style.display = 'none';
        this.redraw();
        if (this.onSave) this.onSave(m);
      } catch(e) { alert('保存に失敗しました'); }
    };'''

txt = txt.replace(old_show, new_show, 1)

with open(p, 'w', encoding='utf-8') as f:
    f.write(txt)

print('OK')
