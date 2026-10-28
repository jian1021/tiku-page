/* 专家库入库考试助手 - Service Worker
 *
 * 缓存策略：
 * - 静态资源（JS/CSS/字体/图片/清单等）：stale-while-revalidate，先返回缓存，同时后台更新。
 * - /api/ 请求：完全不缓存，始终走网络。后端接口本身不返回答案与解析，答错后的解析
 *   只在判分响应中下发，因此答案与解析不会进入离线缓存。
 * - 非 GET 请求：不拦截、不缓存。
 * - 导航请求失败时回退到缓存的 "/"（或 /index.html）。
 */

const CACHE_VERSION = "sx-exam-v1";
const STATIC_CACHE = `sx-static-${CACHE_VERSION}`;
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      // 单个资源失败不影响整体安装
      await Promise.allSettled(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: "reload" }))
        )
      );
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE)
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  // 只处理 GET
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // 只处理同源请求
  if (url.origin !== self.location.origin) return;

  // 接口一律走网络，不缓存（含答案/解析的判分响应不会被持久化）
  if (url.pathname.startsWith("/api/")) return;

  // Service Worker 自身不缓存，便于后续更新
  if (url.pathname.endsWith("/sw.js")) return;

  // 导航请求：网络优先，失败时回退到缓存的首页
  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          return await fetch(request);
        } catch {
          const cache = await caches.open(STATIC_CACHE);
          return (
            (await cache.match("/")) ||
            (await cache.match("/index.html")) ||
            Response.error()
          );
        }
      })()
    );
    return;
  }

  // 静态资源：stale-while-revalidate
  event.respondWith(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      const cached = await cache.match(request);

      const network = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            cache.put(request, response.clone()).catch(() => {});
          }
          return response;
        })
        .catch(() => null);

      return cached || (await network) || Response.error();
    })()
  );
});
