/* ========== Phantom Alert Service Worker ========== */
const VERSION = 'v1.0.3';
const STATIC_CACHE = `static-${VERSION}`;
const RUNTIME_CACHE = `runtime-${VERSION}`;

const PRECACHE_URLS = [
  '/',                         // ルート（HTML）
  '/static/offline.html',
  '/static/bg_cyber_alt2.png',
  '/static/default_chart.png',
  '/static/bgm.mp3',
  '/static/sound_scalp.mp3',
  '/static/buy.mp3',
  '/static/sell.mp3',
  '/static/manifest.webmanifest',
];

// Google Fonts など外部CDNもキャッシュ候補
const FONT_HOSTS = [
  'https://fonts.googleapis.com',
  'https://fonts.gstatic.com',
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC_CACHE);
    await cache.addAll(PRECACHE_URLS);
    // インストール直後から新SWを有効化
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // 古いキャッシュを削除
    const keys = await caches.keys();
    await Promise.all(keys.map(k => {
      if (![STATIC_CACHE, RUNTIME_CACHE].includes(k)) return caches.delete(k);
    }));
    await self.clients.claim();
  })());
});

// 汎用ヘルパー：ナビゲーション要求は network-first → cache → /offline.html
async function handleNavigation(request) {
  try {
    const fresh = await fetch(request);
    const cache = await caches.open(STATIC_CACHE);
    cache.put('/', fresh.clone()).catch(()=>{});
    return fresh;
  } catch (e) {
    const cache = await caches.open(STATIC_CACHE);
    return (await cache.match('/')) 
        || (await cache.match('/static/offline.html'))
        || new Response('Offline', {status: 503});
  }
}

// APIは GET を network-first で取りに行き、失敗時はキャッシュ（最後の成功結果）
// JSONレスポンスのみをキャッシュ対象にする
async function handleApiGet(request) {
  const url = new URL(request.url);
  try {
    const netRes = await fetch(request);
    // 成功したらキャッシュに保存（クローン必須）
    const clone = netRes.clone();
    if (netRes.ok && (clone.headers.get('content-type') || '').includes('application/json')) {
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(url.pathname, clone).catch(()=>{});
    }
    return netRes;
  } catch (e) {
    const cache = await caches.open(RUNTIME_CACHE);
    const cached = await cache.match(url.pathname);
    if (cached) return cached;
    // 代替の空JSON
    return new Response(JSON.stringify({ status: 'offline', data: null }), {
      headers: {'Content-Type':'application/json'},
      status: 200
    });
  }
}

// 静的アセット・フォントは cache-first（なければネット）
async function handleStatic(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const fresh = await fetch(request);
    cache.put(request, fresh.clone()).catch(()=>{});
    return fresh;
  } catch (e) {
    // 画像はデフォルト画像を返す
    if (request.destination === 'image') {
      const fallback = await cache.match('/static/default_chart.png');
      if (fallback) return fallback;
    }
    // それ以外はオフラインページへ
    const offline = await cache.match('/static/offline.html');
    return offline || new Response('Offline', {status: 503});
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // ナビゲーション（HTML遷移）
  if (req.mode === 'navigate') {
    event.respondWith(handleNavigation(req));
    return;
  }

  // API（GETのみをSWで扱う。POST等はそのまま通す）
  if (url.pathname.startsWith('/api/') || url.pathname === '/get_settings') {
    if (req.method === 'GET') {
      event.respondWith(handleApiGet(req));
      return;
    }
    // POST: 通常通りネットへ（index.html側でlocalStorageフォールバック済み）
    return;
  }

  // 静的アセット or フォント
  if (url.pathname.startsWith('/static/') || FONT_HOSTS.some(h => url.origin === h)) {
    event.respondWith(handleStatic(req));
    return;
  }

  // それ以外はデフォルト（ネット→失敗時キャッシュ）
  event.respondWith((async () => {
    try {
      return await fetch(req);
    } catch {
      const cache = await caches.open(STATIC_CACHE);
      const cached = await cache.match(req);
      return cached || (await cache.match('/static/offline.html')) || new Response('Offline', {status: 503});
    }
  })());
});
