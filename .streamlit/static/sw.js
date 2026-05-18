/**
 * Service Worker for Trade AI Assistant PWA.
 *
 * Strategy:
 * - Static assets: Cache-first (CSS, JS, icons)
 * - API/data requests: Network-first with cache fallback
 * - Offline fallback page for navigation requests
 *
 * This enables:
 * - "Add to Home Screen" on mobile
 * - Offline access to recently viewed pages
 * - Faster repeat loads via cached assets
 */

const CACHE_NAME = 'tradeai-v1';
const OFFLINE_URL = '/';

// Static assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/app/static/manifest.json',
];

// ---------------------------------------------------------------------------
// Install: pre-cache core assets
// ---------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  self.skipWaiting();
});

// ---------------------------------------------------------------------------
// Activate: clean old caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// ---------------------------------------------------------------------------
// Fetch: network-first for HTML, cache-first for static assets
// ---------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip WebSocket and Streamlit internal requests
  if (url.pathname.startsWith('/_stcore') || url.pathname.startsWith('/stream')) return;

  // Static assets (images, fonts, CSS, JS) → Cache-first
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Navigation and API requests → Network-first
  event.respondWith(networkFirst(request));
});

// ---------------------------------------------------------------------------
// Caching strategies
// ---------------------------------------------------------------------------

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    // Cache successful HTML responses
    if (response.ok && response.headers.get('content-type')?.includes('text/html')) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Fallback to cache
    const cached = await caches.match(request);
    if (cached) return cached;

    // Offline fallback for navigation
    if (request.mode === 'navigate') {
      return caches.match(OFFLINE_URL);
    }
    return new Response('Offline', { status: 503 });
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isStaticAsset(url) {
  const staticExts = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff2', '.woff', '.css', '.js'];
  return staticExts.some((ext) => url.pathname.endsWith(ext));
}

// ---------------------------------------------------------------------------
// Push notifications (future use)
// ---------------------------------------------------------------------------
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || '你有新的跟进提醒',
    icon: '/app/static/icon-192.png',
    badge: '/app/static/icon-192.png',
    tag: data.tag || 'tradeai-notification',
    data: { url: data.url || '/' },
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '外贸AI助手', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.openWindow(url)
  );
});
