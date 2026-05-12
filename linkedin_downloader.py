#!/usr/bin/env python3
"""
LinkedIn Post Downloader
Lädt Text, Bilder und Videos aus LinkedIn-Posts herunter
und erstellt eine schön lesbare HTML-Datei.

Voraussetzungen:
  python -m pip install requests beautifulsoup4 browser-cookie3

Nutzung:
  python linkedin_downloader.py <url>
  python linkedin_downloader.py <url> --browser firefox
"""

import sys, os, re, json, base64, mimetypes, datetime, argparse, html as html_lib
import requests
from bs4 import BeautifulSoup

# Windows cp1252 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
}


# ── Cookies ───────────────────────────────────────────────────────────────────

def get_browser_cookies(browser: str) -> dict:
    try:
        import browser_cookie3
        fn = getattr(browser_cookie3, browser, None)
        if fn is None:
            print(f'[WARN] Browser "{browser}" nicht unterstützt.')
            return {}
        jar = fn(domain_name='.linkedin.com')
        return {c.name: c.value for c in jar}
    except Exception as e:
        print(f'[WARN] Cookies konnten nicht aus {browser} gelesen werden: {e}')
        return {}


# ── Scraper ───────────────────────────────────────────────────────────────────

def fetch_post(url: str) -> dict:
    """Seite anonym abrufen – liefert vollständiges JSON-LD mit Post-Inhalt."""
    session = requests.Session()
    session.headers.update(HEADERS)
    resp = session.get(url, timeout=15, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    result = {
        'text': '', 'author': '', 'date': '', 'post_url': url, 'images': [],
    }

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
        except Exception:
            continue

        # Autor
        for field in ('author', 'creator'):
            a = data.get(field, {})
            if isinstance(a, dict) and not result['author']:
                result['author'] = a.get('name', '')

        # Datum
        raw_date = data.get('datePublished', '') or data.get('uploadDate', '')
        if raw_date and not result['date']:
            try:
                dt = datetime.datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                result['date'] = dt.strftime('%d.%m.%Y')
            except Exception:
                result['date'] = raw_date[:10]

        # Kanonische URL
        canonical = data.get('@id', '') or data.get('url', '')
        if canonical:
            result['post_url'] = canonical

        # Text – längsten Wert nehmen
        for key in ('description', 'articleBody', 'text', 'headline'):
            val = data.get(key, '')
            if val and len(val) > len(result['text']):
                result['text'] = val.strip()

        # sharedContent (Bild-Posts)
        shared = data.get('sharedContent', {})
        if isinstance(shared, dict):
            for key in ('headline', 'description', 'articleBody'):
                val = shared.get(key, '')
                if val and len(val) > len(result['text']):
                    result['text'] = val.strip()
            if not result['author']:
                sa = shared.get('author', {})
                if isinstance(sa, dict):
                    result['author'] = sa.get('name', '')

    # Fallbacks
    if not result['text']:
        og = soup.find('meta', property='og:description')
        if og:
            result['text'] = (og.get('content') or '').strip()

    if not result['author']:
        og_title = soup.find('meta', property='og:title')
        if og_title:
            parts = [p.strip() for p in (og_title.get('content', '') or '').split('|')]
            if len(parts) >= 2:
                result['author'] = parts[-1].replace('LinkedIn', '').strip() or parts[0]

    # Bilder
    seen = set()
    for tag in soup.find_all('meta', property='og:image'):
        img_url = (tag.get('content') or '').strip()
        if img_url and img_url not in seen:
            seen.add(img_url)
            result['images'].append(img_url)

    return result


# ── Downloads ─────────────────────────────────────────────────────────────────

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
                if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    ext = 'jpg'
            fpath = os.path.join(output_dir, f'image_{i:02d}.{ext}')
            r = session.get(url, timeout=30)
            r.raise_for_status()
            with open(fpath, 'wb') as f:
                f.write(r.content)
            print(f'   -> Bild gespeichert: {fpath}')
            saved.append(fpath)
        except Exception as e:
            print(f'   [WARN] Bild {i} fehlgeschlagen: {e}')
    return saved



# ── HTML-Report ───────────────────────────────────────────────────────────────

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
            try:
                imgs_html += f'<img src="{img_b64(p)}" alt="">'
            except Exception:
                pass
    media_section = f'<div class="media-grid">{imgs_html}</div>' if imgs_html else ''

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
  {media_section}
  <div class="card-footer"><a href="{post.get('post_url', '#')}">{post.get('post_url', '')}</a></div>
</div>
</body>
</html>"""

    fpath = os.path.join(output_dir, safe_filename(post, 'html'))
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(report)
    return fpath


# ── Main ──────────────────────────────────────────────────────────────────────

def download_post(url: str, output_dir: str = 'linkedin_downloads',
                  browser: str = None, profile: str = None):
    os.makedirs(output_dir, exist_ok=True)
    print(f'⬇  Lade herunter: {url}')
    print(f'   Zielordner:    {os.path.abspath(output_dir)}\n')

    cookies = {}
    if browser:
        print(f'   Cookies aus {browser} lesen...')
        cookies = get_browser_cookies(browser)
        print(f'   {len(cookies)} Cookies geladen.\n' if cookies else '   [WARN] Keine Cookies.\n')

    print('   Seite abrufen...')
    try:
        post = fetch_post(url)
    except Exception as e:
        print(f'✗ Fehler: {e}')
        return

    # Text
    print('\n' + '─' * 60)
    if post['author']: print(f"Autor:  {post['author']}")
    if post['date']:   print(f"Datum:  {post['date']}")
    print(f"URL:    {post['post_url']}")
    print('─' * 60)
    print(post['text'] if post['text'] else '[HINWEIS] Kein Text gefunden.')
    print('─' * 60 + '\n')

    # Bilder
    image_paths = []
    if post['images']:
        print(f'   {len(post["images"])} Bild(er) herunterladen...')
        image_paths = download_images(post['images'], output_dir, cookies)

    # HTML-Report
    if post['text'] or image_paths:
        html_path = generate_html_report(post, image_paths, output_dir)
        print(f'\n   -> HTML-Report: {html_path}')

    print(f'\n✓ Fertig! Dateien in: {os.path.abspath(output_dir)}')


def main():
    parser = argparse.ArgumentParser(description='LinkedIn Post Downloader')
    parser.add_argument('url')
    parser.add_argument('--output',  '-o', default='linkedin_downloads')
    parser.add_argument('--browser', '-b',
                        choices=['chrome', 'firefox', 'edge', 'brave', 'chromium',
                                 'opera', 'safari', 'vivaldi', 'whale'])
    parser.add_argument('--profile', '-p', default=None)
    args = parser.parse_args()
    download_post(args.url, args.output, args.browser, args.profile)


if __name__ == '__main__':
    main()
