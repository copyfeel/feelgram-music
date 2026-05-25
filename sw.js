// Feelgram Music — service worker.
//
// Goals:
//  1. Make iOS Safari recognise the app as a fully installed PWA (so the
//     lockscreen Now Playing widget can focus the PWA window).
//  2. Catch the failure case where iOS tries to open the bare audio file URL
//     (e.g. .../music/song.mp3) in Safari — instead of showing a stray "site",
//     intercept the navigation and bounce it back to the PWA root.

const CACHE = 'feelgram-shell-v5';
const SHELL = ['./', './index.html', './manifest.json', './icon.png'];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  // Force each SHELL request to bypass the HTTP cache — c.addAll() goes
  // through the browser cache by default, so without this a stale cached
  // index.html can land in the new CACHE and persist indefinitely.
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(SHELL.map(async (url) => {
      try {
        const res = await fetch(url, { cache: 'reload' });
        if (res && res.ok) await cache.put(url, res);
      } catch (_) {}
    }));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // Drop stale caches from previous versions.
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
    // After a cache-key bump, force every controlled tab/PWA window to
    // reload so they pick up the fresh HTML/CSS/JS immediately — otherwise
    // users see the previous shell until the next manual refresh.
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach((c) => { try { c.navigate(c.url); } catch (_) {} });
  })());
});

// The HTML we return for "wrong" navigations — instructs the browser to focus
// any open client (so the PWA window comes to the front) and falls back to
// loading the root URL.
const REDIRECT_HTML = `<!DOCTYPE html><html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#f6f6f6">
<title>Feelgram Music</title>
<style>html,body{margin:0;background:#f6f6f6;height:100vh;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#888;font-size:13px}</style>
</head><body>
<p>Returning to Feelgram Music…</p>
<script>
// Try to focus an existing PWA window via the service worker. If no PWA
// instance is open, fall through to a hard navigation to the root.
(async () => {
  try {
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage('focus-clients');
    }
  } catch (_) {}
  // Replace the current history entry so back-button doesn't return here.
  location.replace('/');
})();
</script>
</body></html>`;

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 1) Top-level navigation to an audio file URL (the "tap lockscreen widget
  //    opens an unknown site" failure mode on iOS). Bounce to the PWA root.
  if (req.mode === 'navigate' &&
      (/\.(mp3|m4a|wav|ogg|flac|wmv)$/i.test(url.pathname) ||
       url.pathname.startsWith('/music/'))) {
    event.respondWith(
      new Response(REDIRECT_HTML, {
        headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }
      })
    );
    return;
  }

  // 2) Pass-through for actual audio file requests (range-streamed by the
  //    audio element). DO NOT cache — files are large.
  if (/\.(mp3|m4a|wav|ogg|flac|wmv|lrc)$/i.test(url.pathname) ||
      url.pathname.startsWith('/music/') ||
      url.pathname.endsWith('/playlist.json')) {
    return;
  }

  // 3) Network-first for the shell (so deploys propagate immediately) with
  //    cache fallback when offline.
  if (req.mode === 'navigate' ||
      /\.(html|json|png|svg|ico|webmanifest)$/i.test(url.pathname) ||
      url.pathname === '/') {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy).catch(() => {}));
        return res;
      }).catch(() => caches.match(req).then((r) => r || caches.match('./index.html')))
    );
  }
});

// Allow the page (including REDIRECT_HTML) to ping us to focus a PWA window.
self.addEventListener('message', (event) => {
  if (event.data === 'focus-clients') {
    event.waitUntil((async () => {
      const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      // Prefer a standalone PWA window if present
      const pwa = allClients.find((c) => c.frameType === 'top-level' && /standalone|fullscreen|minimal-ui/.test(c.id || ''));
      const target = pwa || allClients[0];
      if (target && 'focus' in target) {
        try { await target.focus(); } catch (_) {}
      }
    })());
  }
});
