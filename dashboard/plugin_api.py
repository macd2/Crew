"""Hermes.Crew dashboard plugin — backend proxy routes.

Mounted at /api/plugins/crew/ by the dashboard plugin system
(hermes_cli.web_server._mount_plugin_api_routes).
Proxies requests to the local crew_graph_serve daemon at http://127.0.0.1:8799.
"""

from __future__ import annotations

import html
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()

UPSTREAM = os.environ.get("CREW_LOCAL_UPSTREAM", "http://127.0.0.1:8799").rstrip("/")

_VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9.-]+(?::[0-9]{1,5})?$")
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_CARD_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_ACK_PATH_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_AVATAR_PATH_RE = re.compile(r"^[a-zA-Z0-9_/-]+\.(?:svg|png)$")


def _sanitize_color(val: str | None) -> str | None:
    if not val:
        return None
    val = val.strip()
    return val.lower() if _HEX_COLOR_RE.match(val) else None


def _public_crew_url(request: Request) -> str:
    """Resolve the public standalone URL for crew based on the client request host."""
    env = (os.environ.get("CREW_DASHBOARD_URL") or "").strip()
    if env:
        return env.rstrip("/")
    raw_proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    proto = "https" if str(raw_proto).strip().lower() == "https" else "http"
    raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:9119"
    raw_host = str(raw_host).strip()
    host = raw_host if _VALID_HOST_RE.match(raw_host) else "127.0.0.1:9119"
    return f"{proto}://{host}/api/plugins/crew/board"


def _forward_request(url: str, request: Request, body: bytes | None = None) -> Response:
    req = urllib.request.Request(url, data=body, method=request.method)

    # Set Host and Origin matching upstream so upstream's same-origin CSRF check passes
    upstream_parts = urllib.parse.urlsplit(UPSTREAM)
    upstream_host = upstream_parts.netloc or "127.0.0.1:8799"
    upstream_origin = f"{upstream_parts.scheme or 'http'}://{upstream_host}"
    req.add_header("Host", upstream_host)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        req.add_header("Origin", upstream_origin)

    for k, v in request.headers.items():
        if k.lower() not in ("host", "content-length", "cookie", "authorization", "origin"):
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "text/plain")
            res_headers: dict[str, str] = {}
            for h_name in ("Content-Type", "Content-Security-Policy", "Cache-Control", "ETag"):
                val = resp.headers.get(h_name)
                if val:
                    res_headers[h_name] = val

            if "text/html" in content_type:
                raw_html = content.decode("utf-8", errors="replace")
                # Rewrite absolute root paths to relative so <base href> resolves them
                raw_html = raw_html.replace('href="/card/', 'href="card/')
                raw_html = raw_html.replace('fetch("/board.json', 'fetch("board.json')
                raw_html = raw_html.replace('fetch("/ack/', 'fetch("ack/')
                raw_html = raw_html.replace('"/card/', '"card/')
                raw_html = raw_html.replace('href="/"', 'href="board"')
                raw_html = raw_html.replace("href='/'", "href='board'")
                raw_html = raw_html.replace('"/avatars/', '"avatars/')
                raw_html = raw_html.replace("'/avatars/", "'avatars/")

                # Fix upper-right link: point to standalone crew board using escaped client hostname
                safe_url = html.escape(_public_crew_url(request), quote=True)

                def _replace_tailnet(m):
                    return (
                        f'<a class="tailnet" href="{safe_url}" target="_blank" rel="noopener noreferrer" '
                        'style="color: #34d399; text-decoration: underline; font-weight: 500;" '
                        'title="Open standalone board in new tab">open in new tab ↗</a>'
                    )

                raw_html = re.sub(r'<a class=tailnet[^>]*>.*?</a>', _replace_tailnet, raw_html)

                # Theme sanitization: strictly validate hex colors and theme mode
                bg_param = _sanitize_color(request.query_params.get("bg"))
                fg_param = _sanitize_color(request.query_params.get("fg"))
                raw_theme = (request.query_params.get("theme") or "").strip().lower()
                theme_param = raw_theme if raw_theme in ("light", "dark") else None

                if bg_param or fg_param or theme_param:
                    theme_bg = bg_param or ("#ffffff" if theme_param == "light" else "#041c1c")
                    theme_fg = fg_param or ("#17171a" if theme_param == "light" else "#ffffff")
                    scheme = theme_param or ("light" if theme_bg.lower() in ("#fff", "#ffffff") else "dark")
                    theme_style = f"""
<style id="hermes-theme-sync">
:root {{
  color-scheme: {scheme} !important;
  --crew-scheme: {scheme} !important;
  --crew-bg: {theme_bg} !important;
  --color-background: {theme_bg} !important;
  --crew-fg: {theme_fg} !important;
  --color-foreground: {theme_fg} !important;
}}
html, body, main#board, main, #main, .page-card {{
  background-color: {theme_bg} !important;
  color: {theme_fg} !important;
}}
</style>
"""
                else:
                    theme_style = ""

                # Inject bridge script for srcdoc iframe mode so fetch uses parent SDK authedFetch
                bridge_script = """
<script id="crew-parent-bridge">
(function() {
  if (window.parent && window.parent !== window && window.parent.__HERMES_PLUGIN_SDK__) {
    var sdk = window.parent.__HERMES_PLUGIN_SDK__;
    if (sdk.authedFetch) {
      var origFetch = window.fetch;
      window.fetch = function(url, init) {
        return sdk.authedFetch(url, init);
      };
    }
  }
})();
</script>
"""
                if "<head>" in raw_html and "<base " not in raw_html:
                    raw_html = raw_html.replace(
                        "<head>",
                        f'<head><base href="/api/plugins/crew/">{theme_style}{bridge_script}',
                        1,
                    )
                content = raw_html.encode("utf-8")

            return Response(content=content, status_code=resp.status, headers=res_headers, media_type=content_type)
    except urllib.error.HTTPError as exc:
        return Response(content=exc.read(), status_code=exc.code, media_type=exc.headers.get("Content-Type", "text/plain"))
    except Exception as exc:
        return Response(
            content=f"<html><body><h3>Crew Dashboard Unavailable</h3><p>Could not reach {UPSTREAM} ({exc}). Ensure the crew daemon is running.</p></body></html>",
            status_code=502,
            media_type="text/html",
        )


@router.get("/board")
async def get_board(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.get("/board.json")
async def get_board_json(request: Request):
    query = str(request.url.query)
    target = f"{UPSTREAM}/board.json" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.api_route("/card/{card_id}", methods=["GET"])
async def get_card(card_id: str, request: Request):
    if not _CARD_ID_RE.match(card_id):
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    quoted_id = urllib.parse.quote(card_id, safe="")
    query = str(request.url.query)
    target = f"{UPSTREAM}/card/{quoted_id}" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.api_route("/ack/{action}", methods=["POST"])
async def post_ack(action: str, request: Request):
    if not _ACK_PATH_RE.match(action):
        raise HTTPException(status_code=400, detail="Invalid ack target format")
    quoted_action = urllib.parse.quote(action, safe="")
    body = await request.body()
    target = f"{UPSTREAM}/ack/{quoted_action}"
    return _forward_request(target, request, body=body)


@router.api_route("/avatars/{avatar_path:path}", methods=["GET"])
async def get_avatars(avatar_path: str, request: Request):
    if ".." in avatar_path or not _AVATAR_PATH_RE.match(avatar_path):
        raise HTTPException(status_code=400, detail="Invalid avatar asset path")
    quoted_path = urllib.parse.quote(avatar_path, safe="/")
    query = str(request.url.query)
    target = f"{UPSTREAM}/avatars/{quoted_path}" + (f"?{query}" if query else "")
    return _forward_request(target, request)


@router.get("/healthz")
async def get_healthz(request: Request):
    target = f"{UPSTREAM}/healthz"
    return _forward_request(target, request)
