/// <reference lib="webworker" />
const CACHE = `ragbase-v${__APP_VERSION__}`;

// 预缓存资源列表（构建后文件由构建工具填充）
const PRECACHE_URLS = ['/'];

// 缓存大小限制配置
const CACHE_SIZE_LIMIT = 50 * 1024 * 1024; // 50MB
const CACHE_SIZE_THRESHOLD = 0.8; // 清理到 80% 以下

// 清理旧缓存，保留最新版本
async function cleanupCaches() {
  const cacheNames = await caches.keys();
  const oldCaches = cacheNames.filter((name) => name !== CACHE);
  await Promise.all(oldCaches.map((name) => caches.delete(name)));
}

// 检查并清理超过大小限制的缓存
async function enforceCacheSizeLimit(cacheName) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  
  // 估算缓存大小并收集条目信息
  let totalSize = 0;
  const entries = [];
  
  for (const request of keys) {
    const response = await cache.match(request);
    if (response) {
      const body = await response.blob();
      totalSize += body.size;
      entries.push({ request, size: body.size });
    }
  }
  
  // 如果超过限制，按 FIFO 顺序删除最旧的条目
  if (totalSize > CACHE_SIZE_LIMIT) {
    // 保持 keys() 返回的顺序（插入顺序），这是真正的 FIFO
    for (const entry of entries) {
      if (totalSize <= CACHE_SIZE_LIMIT * CACHE_SIZE_THRESHOLD) break;
      await cache.delete(entry.request);
      totalSize -= entry.size;
    }
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    cleanupCaches().then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 只处理同源 GET 请求
  if (url.origin !== self.location.origin || request.method !== 'GET') return;

  // API 请求：网络优先，失败时回退到缓存（支持离线）
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => caches.match(request))
    );
    return;
  }

  // 导航请求（HTML）：网络优先，缓存立即提供
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match('/')))
    );
    return;
  }

  // 静态资源（JS、CSS、图片）：stale-while-revalidate 策略
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((response) => {
          // 只缓存成功的响应
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE)
              .then((cache) => cache.put(request, clone))
              .then(() => enforceCacheSizeLimit(CACHE))
              .catch(() => {});
          }
          return response;
        })
        .catch(() => cached || new Response('Offline', { status: 503 }));
      
      return cached || fetchPromise;
    })
  );
});
