"""Minimal HTTP server that serves the offline page during off-hours (10pm–7am UK)."""

import http.server
import os
import socketserver

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FPL Cheat — Offline</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg:       #0d1f17;
      --bg-end:   #132a1f;
      --surface:  #1a2e24;
      --elevated: #243d32;
      --text:     #f5f4f0;
      --muted:    rgba(245,244,240,0.7);
      --dim:      rgba(245,244,240,0.45);
      --accent:   #6b3a9e;
      --border:   rgba(255,255,255,0.1);
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      height: 100%;
      font-family: 'Source Sans 3', system-ui, sans-serif;
      background: linear-gradient(180deg, var(--bg) 0%, var(--bg-end) 50%, var(--bg) 100%);
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .wrap {
      text-align: center;
      padding: 2rem 1.5rem;
      max-width: 480px;
      width: 100%;
    }
    .logo-row {
      display: inline-flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 0.5rem;
    }
    .logo-row img { width: 52px; height: 52px; display: block; flex-shrink: 0; }
    h1 {
      font-family: 'Sora', sans-serif;
      font-size: 2.75rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      color: var(--text);
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2rem 2.5rem;
      margin-top: 2rem;
    }
    .card-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 1.25rem;
      color: var(--text);
    }
    .card h2 {
      font-family: 'Sora', sans-serif;
      font-size: 1.35rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      margin-bottom: 0.75rem;
      color: var(--text);
    }
    .card p {
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.95rem;
    }
    .card p + p { margin-top: 0.4rem; }
    strong { color: var(--text); font-weight: 600; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="logo-row">
      <img src="/favicon.svg" alt="FPL Cheat logo">
      <h1>FPL Cheat</h1>
    </div>
    <div class="card">
      <svg class="card-icon" viewBox="0 0 24 24" fill="#f5f4f0" stroke="#6b3a9e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
      <h2>We're offline for the night</h2>
      <p>To keep costs down, FPL Cheat shuts down between <strong>10pm and 7am UK time</strong>.</p>
      <p>Come back in the morning to check your team!</p>
    </div>
  </div>
</body>
</html>"""

_HTML_BYTES = HTML.encode("utf-8")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/favicon.svg"):
            self._serve_file(os.path.join(_ASSETS_DIR, "favicon.svg"), "image/svg+xml")
        else:
            self._serve_bytes(_HTML_BYTES, "text/html; charset=utf-8")

    def _serve_bytes(self, data: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: str, content_type: str):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self._serve_bytes(data, content_type)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve():
    port = int(os.environ.get("PORT", "8501"))
    with socketserver.TCPServer(("0.0.0.0", port), _Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    serve()
