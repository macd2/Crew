"""Hermes.Crew dashboard plugin — backend proxy routes.

Mounted at /api/plugins/crew/ by the dashboard plugin system
(hermes_cli.web_server._mount_plugin_api_routes), behind Hermes's own auth
middleware: every route here needs the dashboard session token (header) or the
OAuth session cookie, exactly like any other /api/ route. The tab
(dist/index.js) fetches pages with the SDK's authedFetch and renders them into
an iframe via srcdoc; the bridge script injected below routes the page's own
fetch/XHR, card navigation and avatar loads back through that same authedFetch,
so nothing inside the iframe ever needs a credential of its own.

Proxies an allowlisted set of routes to the local crew_graph_serve daemon
(loopback only, CREW_LOCAL_UPSTREAM).
"""

from __future__ import annotations

import html
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

router = APIRouter()

UPSTREAM = os.environ.get("CREW_LOCAL_UPSTREAM", "http://127.0.0.1:8799").rstrip("/")
PREFIX = "/api/plugins/crew/"

_VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9.-]+(?::[0-9]{1,5})?$")
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
# A card id, optionally with the .json suffix the card page polls (card/<id>.json).
_CARD_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+(?:\.json)?$")
_ACK_PATH_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_AVATAR_PATH_RE = re.compile(r"^[a-zA-Z0-9_/-]+\.(?:svg|png)$")
_NONCE_RE = re.compile(r"'nonce-([A-Za-z0-9_+/=-]+)'")

# Request headers forwarded upstream. Everything else - the dashboard session
# token, cookies, Authorization, Origin/Referer, Sec-Fetch-*, X-Forwarded-*,
# Tailscale-User-Login - stays on this side.
_FORWARD_REQUEST_HEADERS = ("accept", "accept-language", "content-type", "if-none-match")
# Response headers passed back to the browser.
_FORWARD_RESPONSE_HEADERS = (
    "Cache-Control", "ETag", "X-Content-Type-Options", "Referrer-Policy",
)
# Query parameters each route forwards upstream (theme params are consumed here).
_BOARD_QUERY = ("all",)
_BOARD_JSON_QUERY = ("all", "older")
_ACK_QUERY = ("undo",)


# Daemon auto-spawn: a Hermes restart does not restart crew_graph_serve, so the proxy starts it on demand.
DAEMON_READY_TIMEOUT = 2.5          # seconds to wait for a freshly spawned daemon to accept connections
DAEMON_SPAWN_COOLDOWN = 10.0        # never spawn more than once per this window (a crashing daemon must not fork-bomb)
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_spawn_lock = threading.Lock()
_last_spawn = {"at": 0.0, "pid": None}


def _upstream_host_port() -> tuple[str, int]:
    parsed = urllib.parse.urlsplit(UPSTREAM)
    return (parsed.hostname or "127.0.0.1"), (parsed.port or 8799)


def _daemon_reachable(timeout: float = 0.5) -> bool:
    host, port = _upstream_host_port()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _hermes_home() -> str:
    env = (os.environ.get("HERMES_HOME") or "").strip()
    if env:
        return env
    try:
        from hermes_constants import get_hermes_home
        return str(get_hermes_home())
    except Exception:
        return os.path.expanduser("~/.hermes")


def _serve_script() -> str | None:
    """crew_graph_serve.py shipped next to this plugin (<plugin>/scripts/). No environment override:
    a dashboard request may start this one file and nothing else."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "scripts", "crew_graph_serve.py")
    return path if os.path.isfile(path) else None


def _spawn_daemon(script: str, host: str, port: int) -> int | None:
    home = _hermes_home()
    env = dict(os.environ)
    env["HERMES_HOME"] = home
    env["CREW_GRAPH_BIND"] = host if host != "localhost" else "127.0.0.1"
    env["CREW_GRAPH_PORT"] = str(port)
    log_dir = os.path.join(home, "logs")
    log_fh = None
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_fh = open(os.path.join(log_dir, "crew_graph_serve.log"), "ab")
    except OSError:
        log_fh = None
    sink = log_fh if log_fh is not None else subprocess.DEVNULL
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": sink, "stderr": sink, "env": env,
              "cwd": os.path.dirname(script), "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0x8)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0x8000000))
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen([sys.executable, script], **kwargs)
    finally:
        if log_fh is not None:
            log_fh.close()
    return proc.pid


def _ensure_daemon_running() -> bool:
    """True when the crew_graph_serve daemon answers on UPSTREAM; spawn it first when it does not.

    Only a loopback UPSTREAM is spawned (a remote one is not ours to start). Spawns are serialized
    and rate-limited; after a spawn it waits up to DAEMON_READY_TIMEOUT seconds for the port.
    """
    if _daemon_reachable():
        return True
    host, port = _upstream_host_port()
    if host.lower() not in _LOOPBACK_HOSTS or os.environ.get("CREW_DAEMON_AUTOSPAWN", "1") == "0":
        return False
    with _spawn_lock:
        if _daemon_reachable():
            return True
        now = time.monotonic()
        if now - _last_spawn["at"] >= DAEMON_SPAWN_COOLDOWN:
            script = _serve_script()
            if not script:
                return False
            try:
                _last_spawn["pid"] = _spawn_daemon(script, host, port)
            except OSError:
                return False
            _last_spawn["at"] = now
        deadline = time.monotonic() + DAEMON_READY_TIMEOUT
        while time.monotonic() < deadline:
            if _daemon_reachable(timeout=0.25):
                return True
            time.sleep(0.1)
        return _daemon_reachable()


def _sanitize_color(val: str | None) -> str | None:
    if not val:
        return None
    val = val.strip()
    return val.lower() if _HEX_COLOR_RE.match(val) else None


def _public_crew_url(request: Request) -> str:
    """The standalone board URL for the "open in new tab" link, from the client's own host.

    Scheme is http or https only; the host must be a bare hostname[:port] (no path,
    quote, whitespace or userinfo) or the loopback default is used. Callers still
    html.escape the result before it goes into markup.
    """
    env = (os.environ.get("CREW_DASHBOARD_URL") or "").strip()
    if env and urllib.parse.urlsplit(env).scheme in ("http", "https") and not any(c in env for c in "\"'<> \t\r\n"):
        return env.rstrip("/")
    raw_proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    proto = "https" if str(raw_proto).strip().lower() == "https" else "http"
    raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:9119"
    raw_host = str(raw_host).strip()
    host = raw_host if _VALID_HOST_RE.match(raw_host) else "127.0.0.1:9119"
    return f"{proto}://{host}{PREFIX}board"


def _upstream_query(request: Request, allowed: tuple[str, ...]) -> str:
    pairs = [(k, v) for k, v in request.query_params.multi_items() if k in allowed]
    return ("?" + urllib.parse.urlencode(pairs)) if pairs else ""


def _proxy_csp(upstream_csp: str) -> str:
    """The upstream nonce policy, with base-uri allowing the <base> this proxy injects."""
    policy = re.sub(r"base-uri[^;]*", "base-uri 'self'", upstream_csp)
    return policy if "base-uri" in policy else policy.rstrip("; ") + "; base-uri 'self'"


# Runs first inside the proxied page. Only acts when the page is the tab's srcdoc
# iframe (same origin, parent exposes the plugin SDK); a page opened directly is
# left alone. Every request the page makes - fetch, XMLHttpRequest, avatar
# images - goes through the parent's authedFetch, and a click on a board/card
# link asks the tab (postMessage) to load that page, because a plain iframe
# navigation carries no session header.
_BRIDGE_JS = r"""(function () {
  var parent = window.parent, sdk;
  try { sdk = parent !== window && parent.__HERMES_PLUGIN_SDK__; } catch (e) { sdk = null; }
  if (!sdk || !sdk.authedFetch) return;
  var origin = parent.location.origin;
  var basePath = new URL(document.baseURI).pathname;
  var hermesBase = parent.__HERMES_BASE_PATH__ || "";
  function rel(u) {
    var url = new URL(String(u), document.baseURI);
    if (url.origin !== origin) return null;
    var p = url.pathname;
    if (p.indexOf(basePath) === 0) p = p.slice(basePath.length);
    else if (p.indexOf(hermesBase + "/api/") === 0) return null;
    else p = p.replace(/^\/+/, "");
    if (p === "" || p === "index.html") p = "board";
    return { path: p, search: url.search };
  }
  function crewFetch(u, init) {
    var r = rel(u);
    if (!r) return Promise.reject(new Error("crew: request outside the plugin: " + u));
    return sdk.authedFetch("/api/plugins/crew/" + r.path + r.search, init);
  }
  window.fetch = function (u, init) { return crewFetch(u && u.url ? u.url : u, init); };
  function FX() { this.readyState = 0; this.status = 0; this.responseText = ""; this._h = {}; }
  FX.prototype.open = function (m, u) { this._m = m; this._u = u; this.readyState = 1; };
  FX.prototype.setRequestHeader = function (k, v) { this._h[k] = v; };
  FX.prototype.abort = function () {};
  FX.prototype._done = function () {
    this.readyState = 4;
    if (this.onreadystatechange) this.onreadystatechange();
    if (this.status && this.onload) this.onload();
    if (!this.status && this.onerror) this.onerror();
  };
  FX.prototype.send = function (body) {
    var x = this;
    crewFetch(x._u, { method: x._m || "GET", headers: x._h, body: body == null ? undefined : body, cache: "no-store" })
      .then(function (r) { x.status = r.status; return r.text(); })
      .then(function (t) { x.responseText = t; x._done(); }, function () { x.status = 0; x._done(); });
  };
  window.XMLHttpRequest = FX;
  function nav(path) { parent.postMessage({ type: "crew:navigate", path: path }, origin); }
  window.__crewNav = function (u) { var r = rel(u); if (r) nav(r.path + r.search); };
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
    var href = a.getAttribute("href");
    if (href.charAt(0) === "#") return;
    var r = rel(href);
    if (!r || !/^(board|card\/[A-Za-z0-9_-]+)$/.test(r.path) || (r.search && r.search !== "?all=1")) return;
    e.preventDefault();
    nav(r.path + r.search);
  }, true);
  // Role faces: an <img src> load sends no session header, so the page's face URL (lib.js faceUrl, rewritten
  // by the proxy to call __crewFace) starts as an empty placeholder naming the face; the observer below
  // fetches it through authedFetch and swaps in a data: URL, cached per face.
  var faces = {}, faceData = {}, MARK = "#crew-face=";
  var BLANK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E";
  window.__crewFace = function (p) { return faceData[p] || (BLANK + MARK + p); };
  function face(img) {
    var src = img.getAttribute("src") || "", path, at = src.indexOf(MARK);
    if (src.indexOf("data:") === 0) {
      if (at === -1) return;
      path = src.slice(at + MARK.length);
    } else {
      var r = rel(src);
      if (!r) return;
      path = r.path;
    }
    if (!/^avatars\/[A-Za-z0-9_\/-]+\.(svg|png)$/.test(path)) return;
    if (!faces[path]) {
      faces[path] = crewFetch(path).then(function (res) {
        if (!res.ok) throw new Error(res.status);
        return res.blob();
      }).then(function (b) {
        return new Promise(function (ok) { var fr = new FileReader(); fr.onload = function () { ok(fr.result); }; fr.readAsDataURL(b); });
      }).then(function (data) { faceData[path] = data; return data; });
    }
    faces[path].then(function (data) { if (img.getAttribute("src") === src) img.setAttribute("src", data); }, function () {});
  }
  function scan(root) {
    if (root.tagName === "IMG") face(root);
    if (root.querySelectorAll) Array.prototype.forEach.call(root.querySelectorAll("img[src]"), face);
  }
  new MutationObserver(function (ms) {
    ms.forEach(function (m) {
      if (m.type === "attributes") face(m.target);
      else Array.prototype.forEach.call(m.addedNodes, function (n) { if (n.nodeType === 1) scan(n); });
    });
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src"] });
  document.addEventListener("DOMContentLoaded", function () { scan(document); });
})();"""


def _theme_style(request: Request) -> str:
    bg_param = _sanitize_color(request.query_params.get("bg"))
    fg_param = _sanitize_color(request.query_params.get("fg"))
    raw_theme = (request.query_params.get("theme") or "").strip().lower()
    theme_param = raw_theme if raw_theme in ("light", "dark") else None
    if not (bg_param or fg_param or theme_param):
        return ""
    theme_bg = bg_param or ("#ffffff" if theme_param == "light" else "#041c1c")
    theme_fg = fg_param or ("#17171a" if theme_param == "light" else "#ffffff")
    scheme = theme_param or ("light" if theme_bg.lower() in ("#fff", "#ffffff") else "dark")
    return f"""
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


def _rewrite_html(raw_html: str, request: Request, csp: str | None) -> str:
    # Absolute upstream paths become relative so the injected <base> resolves them under /api/plugins/crew/.
    raw_html = raw_html.replace('href="/card/', 'href="card/')
    raw_html = raw_html.replace('fetch("/board.json', 'fetch("board.json')
    raw_html = raw_html.replace('fetch("/ack/', 'fetch("ack/')
    raw_html = raw_html.replace('"/card/', '"card/')
    raw_html = raw_html.replace('href="/"', 'href="board"')
    raw_html = raw_html.replace("href='/'", "href='board'")
    raw_html = raw_html.replace('"/avatars/', '"avatars/')
    raw_html = raw_html.replace("'/avatars/", "'avatars/")
    # lib.js faceUrl: inside the tab the bridge supplies the face (see __crewFace in _BRIDGE_JS).
    raw_html = raw_html.replace(
        'return "avatars/role/" + (n || "unknown") + ".svg"; }',
        'var p = "avatars/role/" + (n || "unknown") + ".svg"; return window.__crewFace ? window.__crewFace(p) : p; }',
    )
    # The card page's "o" shortcut: back to the board through the tab, not a bare iframe navigation.
    raw_html = raw_html.replace(
        'window.location.href = "/";',
        '(window.__crewNav ? window.__crewNav("board") : (window.location.href = "board"));',
    )

    # The header link: the standalone board on the client's own (validated, escaped) host.
    safe_url = html.escape(_public_crew_url(request), quote=True)

    def _replace_tailnet(_m):
        return (
            f'<a class="tailnet" href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            'style="color: #34d399; text-decoration: underline; font-weight: 500;" '
            'title="Open standalone board in new tab">open in new tab ↗</a>'
        )

    raw_html = re.sub(r"<a class=tailnet[^>]*>.*?</a>", _replace_tailnet, raw_html)

    if "<head>" not in raw_html or "<base " in raw_html:
        return raw_html
    head = f'<head><base href="{PREFIX}">'
    nonce_attr = ""
    if csp:
        # A srcdoc document never sees response headers: carry the policy in a <meta> as well.
        # frame-ancestors is ignored (and warned about) in a <meta>, so it stays header-only.
        meta_policy = re.sub(r";?\s*frame-ancestors[^;]*", "", csp).strip("; ")
        # Inside srcdoc 'self' is the Hermes dashboard origin, so script-src 'self' would let
        # injected markup load any script the dashboard serves. Crew's scripts are all inline with
        # the nonce (dashboard_asset inlines lib.js/board.js): the meta script-src is nonce-only.
        meta_policy = re.sub(
            r"(script-src)([^;]*)",
            lambda m: m.group(1) + re.sub(r"\s+'self'(?=\s|$)", "", m.group(2)),
            meta_policy,
        )
        head += f'<meta http-equiv="Content-Security-Policy" content="{html.escape(meta_policy, quote=True)}">'
        m = _NONCE_RE.search(csp)
        if m:
            nonce_attr = f' nonce="{html.escape(m.group(1), quote=True)}"'
    head += _theme_style(request)
    head += f'<script id="crew-parent-bridge"{nonce_attr}>{_BRIDGE_JS}</script>'
    return raw_html.replace("<head>", head, 1)


def _forward_once(url: str, request: Request, body: bytes | None = None) -> Response:
    req = urllib.request.Request(url, data=body, method=request.method)

    # Host and Origin name the upstream itself, so crew_graph_serve's Host allowlist and its
    # same-origin write check (_same_origin: Origin netloc == Host) pass for /ack.
    upstream_parts = urllib.parse.urlsplit(UPSTREAM)
    upstream_host = upstream_parts.netloc or "127.0.0.1:8799"
    req.add_header("Host", upstream_host)
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        req.add_header("Origin", f"{upstream_parts.scheme or 'http'}://{upstream_host}")

    for name in _FORWARD_REQUEST_HEADERS:
        val = request.headers.get(name)
        if val:
            req.add_header(name.title(), val)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "text/plain")
            res_headers: dict[str, str] = {}
            for h_name in _FORWARD_RESPONSE_HEADERS:
                val = resp.headers.get(h_name)
                if val:
                    res_headers[h_name] = val
            upstream_csp = resp.headers.get("Content-Security-Policy")
            csp = _proxy_csp(upstream_csp) if upstream_csp else None
            if csp:
                res_headers["Content-Security-Policy"] = csp

            if "text/html" in content_type:
                content = _rewrite_html(content.decode("utf-8", errors="replace"), request, csp).encode("utf-8")

            return Response(content=content, status_code=resp.status, headers=res_headers, media_type=content_type)
    except urllib.error.HTTPError as exc:
        return Response(content=exc.read(), status_code=exc.code, media_type=exc.headers.get("Content-Type", "text/plain"))
    except Exception as exc:
        return Response(
            content=(
                "<html><body><h3>Crew Dashboard Unavailable</h3><p>Could not reach "
                f"{html.escape(UPSTREAM)} ({html.escape(str(exc))}). The crew daemon is not running: the proxy "
                "tried to start crew_graph_serve.py (see $HERMES_HOME/logs/crew_graph_serve.log), or start the "
                "crew dashboard service install.py sets up.</p></body></html>"
            ),
            status_code=502,
            headers={"X-Crew-Upstream": "unreachable"},
            media_type="text/html",
        )


def _forward_request(url: str, request: Request, body: bytes | None = None) -> Response:
    """Forward to the local daemon, starting it first when it is down; retry once after a spawn."""
    _ensure_daemon_running()
    res = _forward_once(url, request, body)
    if res.status_code == 502 and res.headers.get("X-Crew-Upstream") == "unreachable":
        if _ensure_daemon_running():
            res = _forward_once(url, request, body)
    return res


async def _proxy(url: str, request: Request, body: bytes | None = None) -> Response:
    # urllib + a possible spawn wait block: keep them off the dashboard's event loop.
    return await run_in_threadpool(_forward_request, url, request, body)


@router.get("/board")
async def get_board(request: Request):
    return await _proxy(f"{UPSTREAM}/" + _upstream_query(request, _BOARD_QUERY), request)


@router.get("/board.json")
async def get_board_json(request: Request):
    return await _proxy(f"{UPSTREAM}/board.json" + _upstream_query(request, _BOARD_JSON_QUERY), request)


@router.get("/card/{card_id}")
async def get_card(card_id: str, request: Request):
    if not _CARD_ID_RE.match(card_id):
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    return await _proxy(f"{UPSTREAM}/card/{urllib.parse.quote(card_id, safe='.')}", request)


@router.post("/ack/{action}")
async def post_ack(action: str, request: Request):
    if not _ACK_PATH_RE.match(action):
        raise HTTPException(status_code=400, detail="Invalid ack target format")
    body = await request.body()
    target = f"{UPSTREAM}/ack/{urllib.parse.quote(action, safe='')}" + _upstream_query(request, _ACK_QUERY)
    return await _proxy(target, request, body=body)


@router.get("/avatars/{avatar_path:path}")
async def get_avatars(avatar_path: str, request: Request):
    if ".." in avatar_path or not _AVATAR_PATH_RE.match(avatar_path):
        raise HTTPException(status_code=400, detail="Invalid avatar asset path")
    return await _proxy(f"{UPSTREAM}/avatars/{urllib.parse.quote(avatar_path, safe='/')}", request)


@router.get("/healthz")
async def get_healthz(request: Request):
    return await _proxy(f"{UPSTREAM}/healthz", request)
