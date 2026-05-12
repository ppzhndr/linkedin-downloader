#!/usr/bin/env python3
"""
LinkedIn Downloader – Web Interface
Starten: python app.py
Öffnen:  http://localhost:5000
"""

import os, sys, re, json, base64, mimetypes, datetime, queue, threading, html as html_lib
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request, stream_with_context, render_template_string

app = Flask(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
}


# ─────────────────────────────────────────────────────────────────────────────
# Web UI
# ─────────────────────────────────────────────────────────────────────────────

HTML_UI = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LinkedIn Downloader</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d0d0f; --surface: #161618; --border: #252528; --border2: #2e2e33;
    --text: #e8e8ec; --muted: #6b6b78; --accent: #4f8ef7; --accent2: #2563eb;
    --success: #34d399; --error: #f87171; --warn: #fbbf24;
    --mono: 'DM Mono', monospace; --sans: 'DM Sans', sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--sans);
    min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 48px 24px 80px; }
  header { width: 100%; max-width: 680px; margin-bottom: 48px; }
  .logo { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .logo-icon { width: 36px; height: 36px; background: var(--accent); border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 18px; }
  h1 { font-size: 22px; font-weight: 600; letter-spacing: -0.3px; }
  .subtitle { font-size: 13px; color: var(--muted); font-weight: 300; margin-left: 48px; }
  .card { width: 100%; max-width: 680px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin-bottom: 16px; }
  .card-title { font-size: 11px; font-weight: 500; letter-spacing: 0.8px; text-transform: uppercase;
    color: var(--muted); margin-bottom: 20px; }
  label { display: block; font-size: 13px; font-weight: 500; color: var(--muted); margin-bottom: 7px; }
  input[type="text"], input[type="url"], select { width: 100%; background: var(--bg);
    border: 1px solid var(--border2); border-radius: 8px; color: var(--text);
    font-family: var(--mono); font-size: 13px; padding: 11px 14px; outline: none;
    transition: border-color .15s; margin-bottom: 18px; appearance: none; }
  input:focus, select:focus { border-color: var(--accent); }
  input::placeholder { color: var(--muted); }
  select option { background: var(--surface); }
  .select-wrap { position: relative; margin-bottom: 18px; }
  .select-wrap select { margin-bottom: 0; padding-right: 36px; cursor: pointer; }
  .select-wrap::after { content: '▾'; position: absolute; right: 14px; top: 50%;
    transform: translateY(-50%); color: var(--muted); pointer-events: none; font-size: 12px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  button { width: 100%; background: var(--accent); color: #fff; font-family: var(--sans);
    font-size: 14px; font-weight: 500; border: none; border-radius: 8px; padding: 13px;
    cursor: pointer; transition: background .15s; display: flex; align-items: center;
    justify-content: center; gap: 8px; }
  button:hover { background: var(--accent2); }
  button:disabled { opacity: .4; cursor: not-allowed; }
  .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3);
    border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; display: none; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .open-btn { margin-top: 16px; display: none; }
  .open-btn a { display: inline-flex; align-items: center; gap: 8px;
    background: var(--success); color: #0d0d0f; font-weight: 600; font-size: 14px;
    padding: 11px 20px; border-radius: 8px; text-decoration: none; transition: opacity .15s; }
  .open-btn a:hover { opacity: .85; }
  .log-card { width: 100%; max-width: 680px; background: var(--bg);
    border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
    display: none; margin-bottom: 16px; }
  .log-header { display: flex; align-items: center; justify-content: space-between;
    padding: 12px 18px; border-bottom: 1px solid var(--border); background: var(--surface); }
  .log-title { font-size: 11px; font-weight: 500; letter-spacing: .8px; text-transform: uppercase; color: var(--muted); }
  .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); transition: background .3s; }
  .status-dot.running { background: var(--accent); animation: pulse 1s infinite; }
  .status-dot.done    { background: var(--success); animation: none; }
  .status-dot.error   { background: var(--error);   animation: none; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  #log { font-family: var(--mono); font-size: 12.5px; line-height: 1.8;
    padding: 20px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  #log .ok   { color: var(--success); }
  #log .err  { color: var(--error); }
  #log .warn { color: var(--warn); }
  #log .dim  { color: var(--muted); }
  #log .txt  { color: var(--text); }
  .post-card { width: 100%; max-width: 680px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 12px; padding: 24px; display: none; margin-bottom: 16px; }
  .post-meta { font-size: 12px; color: var(--muted); font-family: var(--mono); margin-bottom: 16px; line-height: 1.9; }
  .post-text { font-size: 14px; line-height: 1.75; color: var(--text);
    white-space: pre-wrap; border-left: 2px solid var(--accent); padding-left: 16px; }
  .copy-btn { width: auto; background: transparent; border: 1px solid var(--border2);
    color: var(--muted); font-size: 12px; padding: 7px 14px; border-radius: 6px;
    margin-top: 16px; cursor: pointer; }
  .copy-btn:hover { border-color: var(--accent); color: var(--accent); background: transparent; }
</style>
</head>
<body>
<header>
  <div class="logo"><div class="logo-icon">⬇</div><h1>LinkedIn Downloader</h1></div>
  <p class="subtitle">Text und Bilder aus LinkedIn-Posts als HTML-Datei speichern</p>
</header>

<div class="card">
  <div class="card-title">Post konfigurieren</div>
  <label>LinkedIn Post URL</label>
  <input type="url" id="url" placeholder="https://www.linkedin.com/posts/..." autocomplete="off" spellcheck="false">
  <div class="row">
    <div>
      <label>Browser für Cookies <span style="color:var(--muted);font-weight:300">(optional)</span></label>
      <div class="select-wrap">
        <select id="browser">
          <option value="">– keiner (nur öffentliche Posts) –</option>
          <option value="chrome">Chrome</option>
          <option value="firefox">Firefox</option>
          <option value="edge">Edge</option>
          <option value="brave">Brave</option>
          <option value="chromium">Chromium</option>
          <option value="opera">Opera</option>
          <option value="safari">Safari</option>
          <option value="vivaldi">Vivaldi</option>
          <option value="whale">Whale</option>
        </select>
      </div>
    </div>
    <div>
      <label>Zielordner</label>
      <input type="text" id="output" value="linkedin_downloads" autocomplete="off">
    </div>
  </div>
  <button id="btn" onclick="startDownload()">
    <div class="spinner" id="spinner"></div>
    <span id="btn-label">⬇ Download starten</span>
  </button>
  <div class="open-btn" id="open-btn">
    <a id="open-link" href="#" target="_blank">📄 HTML-Report öffnen</a>
  </div>
</div>

<div class="log-card" id="log-card">
  <div class="log-header">
    <span class="log-title">Ausgabe</span>
    <div class="status-dot" id="status-dot"></div>
  </div>
  <div id="log"></div>
</div>

<div class="post-card" id="post-card">
  <div class="card-title">Post Text</div>
  <div class="post-meta" id="post-meta"></div>
  <div class="post-text" id="post-text"></div>
  <button class="copy-btn" onclick="copyText()">Kopieren</button>
</div>

<script>
  function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function setRunning(state) {
    document.getElementById('btn').disabled = state;
    document.getElementById('spinner').style.display = state ? 'block' : 'none';
    document.getElementById('btn-label').textContent = state ? 'Lädt...' : '⬇ Download starten';
  }
  function colorLine(t) {
    const s = t.trim();
    if (!s) return '<span class="dim"> </span>';
    if (s.startsWith('✓'))                                   return `<span class="ok">${esc(t)}</span>`;
    if (s.startsWith('✗') || /error/i.test(s))              return `<span class="err">${esc(t)}</span>`;
    if (s.startsWith('[HINWEIS]') || s.startsWith('[WARN]')) return `<span class="warn">${esc(t)}</span>`;
    return `<span class="txt">${esc(t)}</span>`;
  }
  function appendLog(text) {
    const log = document.getElementById('log');
    log.innerHTML += colorLine(text) + '\\n';
    log.scrollTop = log.scrollHeight;
  }

  async function startDownload() {
    const url     = document.getElementById('url').value.trim();
    const browser = document.getElementById('browser').value;
    const output  = document.getElementById('output').value.trim() || 'linkedin_downloads';
    if (!url) { alert('Bitte eine LinkedIn URL eingeben.'); return; }
    if (!url.includes('linkedin.com')) { alert('Das sieht nicht wie eine LinkedIn URL aus.'); return; }

    setRunning(true);
    document.getElementById('log').innerHTML = '';
    document.getElementById('log-card').style.display = 'block';
    document.getElementById('post-card').style.display = 'none';
    document.getElementById('open-btn').style.display = 'none';
    document.getElementById('status-dot').className = 'status-dot running';

    try {
      const res = await fetch('/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, browser, output })
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\\n');
        buffer = parts.pop();
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          const raw = part.slice(6);
          if (raw === '__DONE__') break;
          try {
            const msg = JSON.parse(raw);
            if (msg.type === 'log')    appendLog(msg.text);
            if (msg.type === 'post')   showPost(msg);
            if (msg.type === 'report') showReportBtn(msg.path);
            if (msg.type === 'status') document.getElementById('status-dot').className = 'status-dot ' + msg.value;
          } catch {}
        }
      }
    } catch (e) {
      appendLog('✗ Verbindungsfehler: ' + e.message);
      document.getElementById('status-dot').className = 'status-dot error';
    }
    setRunning(false);
  }

  function showPost(msg) {
    let meta = '';
    if (msg.author) meta += `Autor   ${msg.author}\\n`;
    if (msg.date)   meta += `Datum   ${msg.date}\\n`;
    if (msg.url)    meta += `URL     ${msg.url}`;
    document.getElementById('post-meta').textContent = meta;
    document.getElementById('post-text').textContent = msg.text;
    document.getElementById('post-card').style.display = 'block';
  }

  function showReportBtn(path) {
    document.getElementById('open-link').href = '/open?path=' + encodeURIComponent(path);
    document.getElementById('open-btn').style.display = 'block';
  }

  function copyText() {
    navigator.clipboard.writeText(document.getElementById('post-text').textContent).then(() => {
      const btn = document.querySelector('.copy-btn');
      btn.textContent = '✓ Kopiert';
      setTimeout(() => btn.textContent = 'Kopieren', 2000);
    });
  }
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────────────────────

def get_browser_cookies(browser: str) -> dict:
    try:
        import browser_cookie3
        fn = getattr(browser_cookie3, browser, None)
        if fn is None: return {}
        return {c.name: c.value for c in fn(domain_name='.linkedin.com')}
    except Exception:
        return {}


def fetch_post(url: str) -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    resp = session.get(url, timeout=15, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    result = {'text': '', 'author': '', 'date': '', 'post_url': url, 'images': []}

    for script in soup.find_all('script', type='application/ld+json'):
        try: data = json.loads(script.string or '')
        except Exception: continue

        for field in ('author', 'creator'):
            a = data.get(field, {})
            if isinstance(a, dict) and not result['author']:
                result['author'] = a.get('name', '')

        raw_date = data.get('datePublished', '') or data.get('uploadDate', '')
        if raw_date and not result['date']:
            try:
                dt = datetime.datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                result['date'] = dt.strftime('%d.%m.%Y')
            except Exception: result['date'] = raw_date[:10]

        canonical = data.get('@id', '') or data.get('url', '')
        if canonical: result['post_url'] = canonical

        for key in ('description', 'articleBody', 'text', 'headline'):
            val = data.get(key, '')
            if val and len(val) > len(result['text']): result['text'] = val.strip()

        shared = data.get('sharedContent', {})
        if isinstance(shared, dict):
            for key in ('headline', 'description', 'articleBody'):
                val = shared.get(key, '')
                if val and len(val) > len(result['text']): result['text'] = val.strip()
            if not result['author']:
                sa = shared.get('author', {})
                if isinstance(sa, dict): result['author'] = sa.get('name', '')

    if not result['text']:
        og = soup.find('meta', property='og:description')
        if og: result['text'] = (og.get('content') or '').strip()
    if not result['author']:
        og_title = soup.find('meta', property='og:title')
        if og_title:
            parts = [p.strip() for p in (og_title.get('content', '') or '').split('|')]
            if len(parts) >= 2: result['author'] = parts[-1].replace('LinkedIn', '').strip() or parts[0]

    seen = set()
    for tag in soup.find_all('meta', property='og:image'):
        img_url = (tag.get('content') or '').strip()
        if img_url and img_url not in seen:
            seen.add(img_url)
            result['images'].append(img_url)
    return result


def download_images(image_urls: list, output_dir: str, cookies: dict) -> list:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)
    saved = []
    for i, url in enumerate(image_urls, 1):
        try:
            ext = 'jpg'
            clean = url.split('?')[0]
            if '.' in clean.split('/')[-1]:
                ext = clean.split('.')[-1].lower()[:5]
                if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'): ext = 'jpg'
            fpath = os.path.join(output_dir, f'image_{i:02d}.{ext}')
            r = session.get(url, timeout=30)
            r.raise_for_status()
            with open(fpath, 'wb') as f: f.write(r.content)
            saved.append(fpath)
        except Exception:
            pass
    return saved


def safe_filename(post: dict, ext: str) -> str:
    safe_author = re.sub(r'[^\w\s-]', '', post.get('author', ''))[:40].strip().replace(' ', '_')
    safe_date   = (post.get('date') or '').replace('.', '-')
    fname = f"{safe_date}_{safe_author}_post.{ext}" if safe_author else f"{safe_date}_post.{ext}"
    return fname.lstrip('-_') or f'post.{ext}'


def generate_html_report(post: dict, image_paths: list, output_dir: str) -> str:
    def img_b64(path):
        mime = mimetypes.guess_type(path)[0] or 'image/jpeg'
        with open(path, 'rb') as f:
            return f'data:{mime};base64,{base64.b64encode(f.read()).decode()}'

    imgs_html = ''
    for p in image_paths:
        if os.path.exists(p):
            try: imgs_html += f'<img src="{img_b64(p)}" alt="">'
            except Exception: pass
    media = f'<div class="media-grid">{imgs_html}</div>' if imgs_html else ''

    def fmt(text):
        escaped = html_lib.escape(text)
        escaped = re.sub(r'(#\w+)', r'<span class="tag">\1</span>', escaped)
        return escaped.replace('\n', '<br>')

    initial = (post.get('author') or '?')[0].upper()

    report = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(post.get('author', 'LinkedIn Post'))} – {post.get('date', '')}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #f0f2f5; font-family: 'Inter', -apple-system, sans-serif;
  min-height: 100vh; display: flex; justify-content: center; padding: 40px 16px 80px; color: #1a1a1a; }}
.card {{ background: #fff; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08), 0 8px 32px rgba(0,0,0,.07);
  max-width: 680px; width: 100%; overflow: hidden; }}
.card-header {{ padding: 22px 26px 20px; display: flex; align-items: center;
  gap: 14px; border-bottom: 1px solid #f2f2f2; }}
.avatar {{ width: 48px; height: 48px; border-radius: 50%;
  background: linear-gradient(135deg,#0077b5,#00a0dc); color:#fff;
  font-size: 20px; font-weight: 600; display: flex; align-items: center;
  justify-content: center; flex-shrink: 0; }}
.meta {{ flex: 1; min-width: 0; }}
.author {{ font-size: 15px; font-weight: 600; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }}
.dateline {{ display: flex; align-items: center; gap: 8px; margin-top: 3px; font-size: 13px; color: #888; }}
.li-link {{ display: inline-flex; align-items: center; background: #0077b5; color: #fff;
  font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 4px; text-decoration: none; }}
.li-link:hover {{ background: #005f94; }}
.post-body {{ padding: 22px 26px; font-size: 15px; line-height: 1.78; }}
.tag {{ color: #0077b5; font-weight: 500; }}
.media-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2px; background: #e8e8e8; }}
.media-grid img {{ width: 100%; display: block; object-fit: cover; aspect-ratio: 4/3; }}
.media-grid img:only-child {{ aspect-ratio: unset; max-height: 500px; object-fit: contain; background: #000; }}
.card-footer {{ padding: 12px 26px; border-top: 1px solid #f2f2f2;
  font-size: 11.5px; color: #bbb; word-break: break-all; }}
.card-footer a {{ color: #0077b5; text-decoration: none; }}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <div class="avatar">{initial}</div>
    <div class="meta">
      <div class="author">{html_lib.escape(post.get('author', 'Unbekannt'))}</div>
      <div class="dateline">
        <span>{post.get('date', '')}</span>
        <a class="li-link" href="{post.get('post_url', '#')}" target="_blank">LinkedIn ↗</a>
      </div>
    </div>
  </div>
  <div class="post-body">{fmt(post.get('text', ''))}</div>
  {media}
  <div class="card-footer"><a href="{post.get('post_url', '#')}">{post.get('post_url', '')}</a></div>
</div>
</body>
</html>"""

    fpath = os.path.join(output_dir, safe_filename(post, 'html'))
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(report)
    return fpath


def run_download(url, output_dir, browser, q):
    def log(text): q.put({'type': 'log', 'text': text})

    os.makedirs(output_dir, exist_ok=True)
    log('Seite abrufen...')

    cookies = {}
    if browser:
        log(f'Cookies aus {browser} lesen...')
        cookies = get_browser_cookies(browser)
        log(f'{len(cookies)} Cookies geladen.' if cookies else '[WARN] Keine Cookies gefunden.')

    try:
        post = fetch_post(url)
    except Exception as e:
        log(f'✗ Fehler beim Abrufen: {e}')
        q.put({'type': 'status', 'value': 'error'})
        q.put(None)
        return

    if post['text']:
        q.put({'type': 'post', 'text': post['text'], 'author': post['author'],
               'date': post['date'], 'url': post['post_url']})
    else:
        log('[HINWEIS] Kein Post-Text gefunden.')

    image_paths = []
    if post['images']:
        log(f'{len(post["images"])} Bild(er) herunterladen...')
        image_paths = download_images(post['images'], output_dir, cookies)
        log(f'-> {len(image_paths)} Bild(er) gespeichert.')

    if post['text'] or image_paths:
        log('HTML-Report erstellen...')
        html_path = generate_html_report(post, image_paths, output_dir)
        log(f'-> Report gespeichert: {os.path.basename(html_path)}')
        q.put({'type': 'report', 'path': html_path})

    log(f'✓ Fertig! Dateien in: {os.path.abspath(output_dir)}')
    q.put({'type': 'status', 'value': 'done'})
    q.put(None)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML_UI)


@app.route('/download', methods=['POST'])
def download():
    data    = request.get_json()
    url     = data.get('url', '').strip()
    browser = data.get('browser', '').strip() or None
    output  = data.get('output', 'linkedin_downloads').strip() or 'linkedin_downloads'
    q = queue.Queue()
    threading.Thread(target=run_download, args=(url, output, browser, q), daemon=True).start()

    def generate():
        while True:
            item = q.get()
            if item is None:
                yield 'data: __DONE__\n\n'
                break
            yield f'data: {json.dumps(item, ensure_ascii=False)}\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/open')
def open_file():
    path = request.args.get('path', '')
    if not path or not os.path.exists(path):
        return 'Datei nicht gefunden.', 404
    with open(path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}


if __name__ == '__main__':
    print('─' * 50)
    print('  LinkedIn Downloader')
    print('  → http://localhost:5000')
    print('─' * 50)
    app.run(debug=False, port=5000)
