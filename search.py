#!/usr/bin/env python3
"""Tiny local web-search proxy for the Robotron avatar.

Why this exists: a browser page can't call search engines directly (CORS), and the
local model has no internet. This proxy does the search server-side and returns clean
JSON with permissive CORS so the page can fetch it. No API keys. Stdlib only.

Run:  python3 search.py            # serves on http://localhost:8765
Test: python3 search.py test "your query here"
Endpoint: GET /search?q=...  ->  {"results":[{"title","snippet","url"}, ...]}
"""
import sys, re, json, html, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def _clean(s):
    return html.unescape(re.sub("<.*?>", "", s)).strip()

def _real_url(href):
    # DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<encoded>
    m = re.search(r"uddg=([^&]+)", href)
    return urllib.parse.unquote(m.group(1)) if m else href

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")

def search(q, n=5):
    """Search DuckDuckGo (HTML endpoint, with the lite endpoint as fallback)."""
    results = []
    try:
        page = _fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
        titles = re.findall(r'class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>', page, re.S)
        snips  = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
        for i, (href, title) in enumerate(titles[:n]):
            results.append({
                "title": _clean(title),
                "url": _real_url(href),
                "snippet": _clean(snips[i]) if i < len(snips) else "",
            })
    except Exception as e:
        sys.stderr.write("html endpoint failed: %s\n" % e)

    if not results:  # fallback: lite endpoint (simpler markup)
        try:
            page = _fetch("https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(q))
            for href, title in re.findall(r'<a[^>]*class="result-link"[^>]*href="(.*?)"[^>]*>(.*?)</a>', page, re.S)[:n]:
                results.append({"title": _clean(title), "url": _real_url(href), "snippet": ""})
        except Exception as e:
            sys.stderr.write("lite endpoint failed: %s\n" % e)
    return results

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/search":
            self.send_response(404); self._cors(); self.end_headers(); return
        q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
        try:
            body = json.dumps({"query": q, "results": search(q)}).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"error": str(e), "results": []}).encode()
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass  # quiet

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print(json.dumps(search(" ".join(sys.argv[2:]) or "test"), indent=2))
    else:
        print("search proxy on http://localhost:%d/search?q=..." % PORT)
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
