// Cloudflare Worker — proxies the Feelgram soundtrack release assets
// hosted on GitHub Releases. GitHub responds with
//   Content-Type: application/octet-stream
//   Content-Disposition: attachment; filename=…
// and no CORS headers, which makes iOS Safari refuse to play the asset
// through a <video> element. This Worker re-emits the stream with the
// correct MIME type, CORS, and Range support so the player works.
//
// Deploy:
//   1) https://dash.cloudflare.com → Workers & Pages → Create
//   2) Paste this file's contents into the editor
//   3) Save and Deploy — copy the resulting *.workers.dev URL
//   4) Tell Claude the URL; SOUNDTRACK_BASE_URL in index.html will be
//      updated to point at the proxy instead of github.com directly.

const RELEASE_BASE =
  'https://github.com/copyfeel/feelgram-music/releases/download/soundtrack-v1/';

const MIME_MAP = {
  mp4: 'video/mp4',
  m4v: 'video/x-m4v',
  mov: 'video/quicktime',
  webm: 'video/webm',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
};

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
  'Access-Control-Allow-Headers': 'Range, Content-Type',
  'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
  'Access-Control-Max-Age': '86400',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const filename = url.pathname.replace(/^\/+/, '');
    if (!filename) return new Response('Not found', { status: 404 });

    const upstream = await fetch(RELEASE_BASE + encodeURIComponent(filename), {
      method: request.method,
      headers: passUpstreamHeaders(request.headers),
      redirect: 'follow',
    });

    const ext = filename.split('.').pop().toLowerCase();
    const mime = MIME_MAP[ext] || 'application/octet-stream';

    const outHeaders = new Headers(CORS_HEADERS);
    outHeaders.set('Content-Type', mime);
    outHeaders.set('Cache-Control', 'public, max-age=31536000, immutable');
    copyHeader(upstream.headers, outHeaders, 'Content-Length');
    copyHeader(upstream.headers, outHeaders, 'Content-Range');
    copyHeader(upstream.headers, outHeaders, 'Accept-Ranges');
    copyHeader(upstream.headers, outHeaders, 'ETag');

    return new Response(upstream.body, {
      status: upstream.status,
      headers: outHeaders,
    });
  },
};

function passUpstreamHeaders(src) {
  const h = new Headers();
  const range = src.get('Range');
  if (range) h.set('Range', range);
  return h;
}
function copyHeader(src, dst, name) {
  const v = src.get(name);
  if (v != null) dst.set(name, v);
}
