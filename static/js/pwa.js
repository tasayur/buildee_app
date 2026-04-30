/* ============================================================
   BuildeeMgr — pwa.js
   Service Worker 登録 + A2HS バナー + オフライン表示
   ============================================================ */

(function () {
  'use strict';

  // ===== 1. Service Worker 登録 =====
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/sw.js', { scope: '/' })
        .then(reg => {
          console.log('[PWA] SW registered. Scope:', reg.scope);

          // 更新検出 → バナー表示
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                showUpdateBanner();
              }
            });
          });
        })
        .catch(err => console.warn('[PWA] SW registration failed:', err));

      // SW更新後のリロード
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (!refreshing) { refreshing = true; window.location.reload(); }
      });
    });
  }

  // ===== 2. 最終オンライン時刻を保存 =====
  if (navigator.onLine) {
    localStorage.setItem('lastOnline', Date.now().toString());
  }
  window.addEventListener('online', () => {
    localStorage.setItem('lastOnline', Date.now().toString());
  });

  // ===== 3. オフライン表示バー =====
  function createOfflineBar() {
    const bar = document.createElement('div');
    bar.id = 'offlineBar';
    bar.innerHTML = '<i class="fa-solid fa-wifi-slash"></i> オフラインです。キャッシュデータを表示中。';
    bar.style.cssText = `
      display:none; position:fixed; top:0; left:0; right:0; z-index:9999;
      background:#dc2626; color:#fff; text-align:center;
      padding:10px 16px; font-size:13px; font-weight:600;
      box-shadow:0 2px 8px rgba(0,0,0,0.25); gap:8px;
      align-items:center; justify-content:center;
    `;
    document.body.appendChild(bar);
    return bar;
  }

  const offlineBar = createOfflineBar();

  function updateNetworkUI() {
    if (navigator.onLine) {
      offlineBar.style.display = 'none';
      document.body.style.paddingTop = '';
    } else {
      offlineBar.style.display = 'flex';
      document.body.style.paddingTop = '42px';
    }
  }

  window.addEventListener('online',  updateNetworkUI);
  window.addEventListener('offline', updateNetworkUI);
  updateNetworkUI(); // 初期状態

  // ===== 4. A2HS（ホーム画面追加）バナー =====
  let deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // すでにインストール済みならスキップ
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    if (localStorage.getItem('a2hs_dismissed')) return;

    showInstallBanner();
  });

  function showInstallBanner() {
    if (document.getElementById('installBanner')) return;

    const banner = document.createElement('div');
    banner.id = 'installBanner';
    banner.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <img src="/static/icons/icon-72x72.png" width="44" height="44"
             style="border-radius:10px;flex-shrink:0" alt="icon">
        <div style="flex:1;min-width:140px">
          <div style="font-weight:700;font-size:14px">BuildeeMgr をインストール</div>
          <div style="font-size:12px;opacity:0.85;margin-top:2px">ホーム画面に追加してオフラインでも使用可能</div>
        </div>
        <div style="display:flex;gap:8px;flex-shrink:0">
          <button id="installBtn" onclick="triggerInstall()"
            style="background:#f97316;color:#fff;border:none;border-radius:8px;
                   padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;
                   white-space:nowrap">
            インストール
          </button>
          <button onclick="dismissInstallBanner()"
            style="background:rgba(255,255,255,0.15);color:#fff;border:none;
                   border-radius:8px;padding:9px 14px;font-size:13px;cursor:pointer">
            後で
          </button>
        </div>
      </div>`;
    banner.style.cssText = `
      position:fixed; bottom:0; left:0; right:0; z-index:9998;
      background:linear-gradient(135deg,#1a1a2e,#16213e);
      color:#fff; padding:14px 16px;
      box-shadow:0 -4px 20px rgba(0,0,0,0.3);
      border-top:1px solid rgba(255,255,255,0.1);
      animation: slideUpBanner 0.4s ease;
    `;

    // アニメーション style
    if (!document.getElementById('pwaAnimStyle')) {
      const s = document.createElement('style');
      s.id = 'pwaAnimStyle';
      s.textContent = `
        @keyframes slideUpBanner { from{transform:translateY(100%);opacity:0} to{transform:translateY(0);opacity:1} }
        @keyframes fadeInUpdate  { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
      `;
      document.head.appendChild(s);
    }

    document.body.appendChild(banner);

    // ボトムナビと重ならないよう余白調整
    const bottomNav = document.getElementById('bottomNav');
    if (bottomNav) banner.style.bottom = window.innerWidth <= 768 ? '64px' : '0';
  }

  window.triggerInstall = async function () {
    if (!deferredPrompt) return;
    const btn = document.getElementById('installBtn');
    if (btn) { btn.textContent = '処理中...'; btn.disabled = true; }
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    dismissInstallBanner();
    if (outcome === 'accepted') {
      showToast('✅ ホーム画面に追加しました！', 'success', 4000);
    }
  };

  window.dismissInstallBanner = function () {
    const banner = document.getElementById('installBanner');
    if (banner) {
      banner.style.animation = 'none';
      banner.style.transition = 'transform 0.3s, opacity 0.3s';
      banner.style.transform = 'translateY(100%)';
      banner.style.opacity = '0';
      setTimeout(() => banner.remove(), 300);
    }
    localStorage.setItem('a2hs_dismissed', '1');
    // 7日後にリセット
    setTimeout(() => localStorage.removeItem('a2hs_dismissed'), 7 * 24 * 3600 * 1000);
  };

  // インストール完了検出
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    dismissInstallBanner();
    console.log('[PWA] App installed!');
  });

  // ===== 5. アップデートバナー =====
  function showUpdateBanner() {
    if (document.getElementById('updateBanner')) return;
    const banner = document.createElement('div');
    banner.id = 'updateBanner';
    banner.innerHTML = `
      <i class="fa-solid fa-rotate-right"></i>
      &nbsp;アップデートがあります&nbsp;
      <button onclick="applyUpdate()" style="background:#fff;color:#1d4ed8;border:none;
        border-radius:6px;padding:5px 12px;font-size:12px;font-weight:700;cursor:pointer;margin-left:8px">
        今すぐ更新
      </button>
      <button onclick="this.parentElement.remove()" style="background:transparent;color:rgba(255,255,255,0.7);
        border:none;cursor:pointer;font-size:16px;margin-left:8px">✕</button>`;
    banner.style.cssText = `
      position:fixed; top:56px; left:0; right:0; z-index:9997;
      background:#1d4ed8; color:#fff; text-align:center;
      padding:10px 16px; font-size:13px; font-weight:600;
      display:flex; align-items:center; justify-content:center; gap:4px;
      animation: fadeInUpdate 0.3s ease;
    `;
    document.body.appendChild(banner);
  }

  window.applyUpdate = function () {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then(reg => {
        if (reg.waiting) reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      });
    }
    window.location.reload();
  };

  // ===== 6. iOS Safari 用インストール案内 =====
  function isIOS() {
    return /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
  }
  function isInStandaloneMode() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
  }

  if (isIOS() && !isInStandaloneMode() && !localStorage.getItem('ios_hint_shown')) {
    setTimeout(() => {
      showIOSHint();
      localStorage.setItem('ios_hint_shown', '1');
    }, 3000);
  }

  function showIOSHint() {
    const hint = document.createElement('div');
    hint.id = 'iosHint';
    hint.innerHTML = `
      <div style="font-weight:700;font-size:14px;margin-bottom:6px">
        <i class="fa-brands fa-apple"></i> ホーム画面に追加する方法
      </div>
      <div style="font-size:13px;opacity:0.9;line-height:1.6">
        Safari の <b>共有ボタン <i class="fa-solid fa-arrow-up-from-bracket"></i></b> をタップ →<br>
        「<b>ホーム画面に追加</b>」を選択してください
      </div>
      <div style="margin-top:4px;text-align:center">
        <i class="fa-solid fa-chevron-down" style="font-size:20px;opacity:0.6;animation:pulse2 1.5s infinite"></i>
      </div>`;
    hint.style.cssText = `
      position:fixed; bottom:80px; left:16px; right:16px; z-index:9998;
      background:linear-gradient(135deg,#1a1a2e,#16213e);
      color:#fff; border-radius:16px; padding:18px 20px;
      box-shadow:0 8px 32px rgba(0,0,0,0.4);
      border:1px solid rgba(255,255,255,0.15);
    `;
    const style = document.createElement('style');
    style.textContent = '@keyframes pulse2{0%,100%{opacity:0.5}50%{opacity:1}}';
    document.head.appendChild(style);

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'position:absolute;top:10px;right:14px;background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer';
    closeBtn.onclick = () => hint.remove();
    hint.appendChild(closeBtn);
    document.body.appendChild(hint);
    setTimeout(() => hint.remove(), 12000);
  }

})();
