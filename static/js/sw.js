/* ============================================================
   BuildeeMgr Service Worker  — Cache-First + Network Fallback
   ============================================================ */

const CACHE_NAME   = 'buildee-v1.0.0';
const API_CACHE    = 'buildee-api-v1.0.0';
const OFFLINE_URL  = '/offline';

// ===== キャッシュするアセット (Install時) =====
const PRECACHE_ASSETS = [
  '/',
  '/coordination',
  '/ky',
  '/safety',
  '/attendance',
  '/offline',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/icons/apple-touch-icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js'
];

// ===== INSTALL — Precache =====
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Precaching assets...');
      // 外部CDNは失敗してもインストール続行
      return Promise.allSettled(
        PRECACHE_ASSETS.map(url =>
          cache.add(url).catch(e => console.warn('[SW] Precache miss:', url, e.message))
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ===== ACTIVATE — 古いキャッシュを削除 =====
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== API_CACHE)
          .map(k => {
            console.log('[SW] Deleting old cache:', k);
            return caches.delete(k);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ===== FETCH — ルーティング戦略 =====
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Chrome DevTools や非HTTPは無視
  if (!url.protocol.startsWith('http')) return;

  // ===== API呼び出し: Network-First, キャッシュFallback =====
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstAPI(request));
    return;
  }

  // ===== 静的アセット: Cache-First =====
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('cloudflare') ||
    url.hostname.includes('cdnjs')
  ) {
    event.respondWith(cacheFirstStatic(request));
    return;
  }

  // ===== ページナビゲーション: Network-First, Offline fallback =====
  if (request.mode === 'navigate') {
    event.respondWith(networkFirstPage(request));
    return;
  }

  // ===== その他: Network-First =====
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

// ----- Network-First (API) -----
async function networkFirstAPI(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'offline', message: 'オフライン中です' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ----- Cache-First (Static assets) -----
async function cacheFirstStatic(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (e) {
    return new Response('', { status: 404 });
  }
}

// ----- Network-First (Page navigation) -----
async function networkFirstPage(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return caches.match(OFFLINE_URL) || new Response('<h1>オフライン</h1>', {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
}

// ===== PUSH通知 (将来拡張用) =====
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'BuildeeMgr', {
      body:  data.body  || '',
      icon:  '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-72x72.png',
      tag:   data.tag   || 'buildee',
      data:  { url: data.url || '/' }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});
