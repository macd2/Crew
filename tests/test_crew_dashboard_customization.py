"""Dashboard plugin proxy (dashboard/plugin_api.py) driven through FastAPI's TestClient.

Covers the PR #3 review: the escaped public host, the allowlisted routes, the
401 a caller without the dashboard session token gets from Hermes's own auth
middleware, the CSP + nonce on the page the tab renders via srcdoc, and an /ack
write that reaches a real crew_graph_serve and passes its same-origin check.
"""
import html
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
CREW_ROOT = os.path.dirname(HERE)
for p in (CREW_ROOT, os.path.join(CREW_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from dashboard import plugin_api  # noqa: E402
from dashboard.plugin_api import (  # noqa: E402
    router,
    _sanitize_color,
    _public_crew_url,
    _CARD_ID_RE,
    _ACK_PATH_RE,
    _AVATAR_PATH_RE,
)

UPSTREAM_CSP = ("default-src 'self'; script-src 'self' 'nonce-abc123'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'")


def _load_hermes_auth():
    """Hermes's real web_server auth middleware, imported under a throwaway HERMES_HOME.

    None when hermes-agent is not installed (the crew suite also runs without it).
    """
    saved = {k: os.environ.get(k) for k in ("HERMES_HOME", "HERMES_DASHBOARD_SESSION_TOKEN")}
    os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="crew-dash-home-")
    os.environ["HERMES_DASHBOARD_SESSION_TOKEN"] = "crew-test-session-token"
    try:
        import hermes_cli.web_server as ws
    except Exception:
        return None
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if not hasattr(ws, "auth_middleware") or not hasattr(ws, "_SESSION_TOKEN"):
        return None
    return ws


def _mock_upstream(mock_urlopen, body, content_type, csp=None, status=200):
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8") if isinstance(body, str) else body
    resp.status = status
    headers = {"Content-Type": content_type}
    if csp:
        headers["Content-Security-Policy"] = csp
    resp.headers = headers
    mock_urlopen.return_value.__enter__.return_value = resp
    return resp


class CrewDashboardCustomizationTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(self.app)

    def test_manifest_metadata(self):
        manifest_path = os.path.join(CREW_ROOT, "dashboard", "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("name"), "crew")
        self.assertEqual(data.get("tab", {}).get("path"), "/crew")
        self.assertEqual(data.get("entry"), "dist/index.js")
        self.assertEqual(data.get("api"), "plugin_api.py")
        # The tab ships with the plugin it belongs to: one version for both.
        with open(os.path.join(CREW_ROOT, "plugin.yaml"), "r", encoding="utf-8") as f:
            plugin_version = next(l.split(":", 1)[1].strip() for l in f if l.startswith("version:"))
        self.assertEqual(data.get("version"), plugin_version)

    def test_dist_index_js_never_holds_a_credential(self):
        with open(os.path.join(CREW_ROOT, "dashboard", "dist", "index.js"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hand-written ES5", content)
        for leak in ("_SESSION_TOKEN", "__HERMES_SESSION_TOKEN__", "X-Hermes-Session-Token", "token="):
            self.assertNotIn(leak, content)

    def test_color_sanitization_rejects_xss(self):
        self.assertEqual(_sanitize_color("#041c1c"), "#041c1c")
        self.assertEqual(_sanitize_color("#fff"), "#fff")
        self.assertEqual(_sanitize_color("#AABBCC"), "#aabbcc")
        for bad in ("</style><script>alert(1)</script>", "#041c1c; alert(1)", "red; background: blue",
                    "expression(alert(1))", "rgba(0,0,0,1)"):
            self.assertIsNone(_sanitize_color(bad), bad)

    def test_public_crew_url_sanitization(self):
        ok = MagicMock()
        ok.headers = {"host": "agent.example.com", "x-forwarded-proto": "https"}
        ok.url.scheme = "https"
        self.assertEqual(_public_crew_url(ok), "https://agent.example.com/api/plugins/crew/board")

        for host, proto in (('attacker.com" onclick="alert(1)', "javascript:alert(1)"),
                            ("evil.com/path", "http"), ("evil.com\\x", "http"), ("a b", "http"),
                            ("user@evil.com", "http"), ("evil.com'><script>", "https ")):
            hostile = MagicMock()
            hostile.headers = {"host": host, "x-forwarded-proto": proto}
            hostile.url.scheme = "http"
            url = _public_crew_url(hostile)
            self.assertRegex(url, r"^https?://127\.0\.0\.1:9119/api/plugins/crew/board$", host)

    def test_route_allowlisting_and_validation(self):
        self.assertTrue(_CARD_ID_RE.match("t_12345"))
        self.assertTrue(_CARD_ID_RE.match("card-abc_12"))
        self.assertTrue(_CARD_ID_RE.match("t_12345.json"))
        for bad in ("../../etc/passwd", "card/subpath", "t_1.json.json", "t_1.html", ".json"):
            self.assertFalse(_CARD_ID_RE.match(bad), bad)
        self.assertTrue(_ACK_PATH_RE.match("all"))
        self.assertTrue(_ACK_PATH_RE.match("t_12345"))
        self.assertFalse(_ACK_PATH_RE.match("all/extra"))
        self.assertTrue(_AVATAR_PATH_RE.match("role/worker.svg"))
        self.assertTrue(_AVATAR_PATH_RE.match("role/verifier.png"))
        self.assertFalse(_AVATAR_PATH_RE.match("../secret.txt"))
        self.assertFalse(_AVATAR_PATH_RE.match("role/worker.exe"))

    @patch("urllib.request.urlopen")
    def test_only_allowlisted_routes_reach_upstream(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "{}", "application/json")
        for path in ("/api/plugins/crew/index.json", "/api/plugins/crew/scripts/crew_card.py",
                     "/api/plugins/crew/card/t_1/extra", "/api/plugins/crew/avatars/role/../../x.svg",
                     "/api/plugins/crew/card/t_1%3Fall%3D1", "/api/plugins/crew/card/..%2F..%2Fx"):
            self.assertIn(self.client.get(path).status_code, (400, 404, 405), path)
        self.assertEqual(self.client.get("/api/plugins/crew/ack/all").status_code, 405)   # writes are POST only
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_card_json_poll_is_proxied(self, mock_urlopen):
        _mock_upstream(mock_urlopen, '{"card_id": "t_abc"}', "application/json")
        resp = self.client.get("/api/plugins/crew/card/t_abc.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"card_id": "t_abc"})
        self.assertEqual(mock_urlopen.call_args[0][0].full_url, "http://127.0.0.1:8799/card/t_abc.json")

    @patch("urllib.request.urlopen")
    def test_query_and_headers_forwarded_upstream_are_allowlisted(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "{}", "application/json")
        self.client.get(
            "/api/plugins/crew/board.json?all=1&older=1&token=secret&x=%2F..",
            headers={"X-Hermes-Session-Token": "secret", "Authorization": "Bearer secret",
                     "Cookie": "hermes_session=secret", "X-Forwarded-For": "1.2.3.4",
                     "Tailscale-User-Login": "owner@example.com", "Accept": "application/json"},
        )
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8799/board.json?all=1&older=1")
        sent = {k.lower(): v for k, v in req.header_items()}
        for name in ("x-hermes-session-token", "authorization", "cookie", "x-forwarded-for",
                     "tailscale-user-login"):
            self.assertNotIn(name, sent)
        self.assertNotIn("secret", json.dumps(sent))
        self.assertEqual(sent.get("accept"), "application/json")

    @patch("urllib.request.urlopen")
    def test_board_page_escapes_host_and_keeps_the_nonce_csp(self, mock_urlopen):
        upstream = (
            "<!doctype html><html><head><title>Crew</title></head><body>"
            "<span class=node>pc - kanban <a class=tailnet href='http://127.0.0.1:8799/'>link</a></span>"
            '<a href="/card/t_123">Task</a><a class="brand" href="/">Crew</a>'
            '<img src="/avatars/role/worker.svg">'
            '<script nonce="abc123">fetch("/board.json");'
            'function faceUrl(n){ return "/avatars/role/" + (n || "unknown") + ".svg"; }</script>'
            "</body></html>"
        )
        _mock_upstream(mock_urlopen, upstream, "text/html; charset=utf-8", csp=UPSTREAM_CSP)

        resp = self.client.get(
            "/api/plugins/crew/board?bg=%3C/style%3E%3Cscript%3Ealert(1)%3C/script%3E",
            headers={"X-Forwarded-Host": 'evil.com" onmouseover="alert(2)', "X-Forwarded-Proto": "javascript"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        self.assertNotIn("alert(1)", body)
        self.assertNotIn("alert(2)", body)
        self.assertNotIn("javascript", body.split("crew-parent-bridge")[0])
        self.assertIn('href="http://127.0.0.1:9119/api/plugins/crew/board" target="_blank"', body)
        self.assertNotIn("set-cookie", resp.headers)

        # Header CSP: the upstream nonce policy, with base-uri opened for the injected <base>.
        csp = resp.headers.get("content-security-policy")
        self.assertIn("'nonce-abc123'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertNotIn("base-uri 'none'", csp)
        # srcdoc never sees response headers: the same policy rides in a <meta>, minus frame-ancestors.
        self.assertIn('<meta http-equiv="Content-Security-Policy" content="default-src', body)
        self.assertNotIn("frame-ancestors", body)
        # Inside srcdoc 'self' is the dashboard origin: the meta policy's script-src is nonce-only.
        meta_m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', body)
        self.assertIsNotNone(meta_m)
        meta_policy = html.unescape(meta_m.group(1))
        script_src = re.search(r"script-src[^;]*", meta_policy).group(0)
        self.assertIn("'nonce-abc123'", script_src)
        self.assertNotIn("'self'", script_src)
        self.assertEqual(script_src.split(), ["script-src", "'nonce-abc123'"])
        # Only script-src loses 'self'; the other directives keep it.
        self.assertIn("default-src 'self'", meta_policy)
        self.assertIn("connect-src 'self'", meta_policy)
        # The header policy is untouched.
        self.assertIn("script-src 'self' 'nonce-abc123'", csp)
        # The injected bridge carries the page's nonce, so that policy lets it run.
        self.assertIn('<script id="crew-parent-bridge" nonce="abc123">', body)
        self.assertLess(body.index('<base href="/api/plugins/crew/">'), body.index("crew-parent-bridge"))
        # Root-absolute links are made relative to the <base>.
        self.assertIn('href="card/t_123"', body)
        self.assertIn('href="board"', body)
        self.assertIn('src="avatars/role/worker.svg"', body)
        self.assertIn('fetch("board.json")', body)
        # An <img> load carries no session header: inside the tab the bridge supplies the role face.
        self.assertIn('return window.__crewFace ? window.__crewFace(p) : p; }', body)

    @patch("urllib.request.urlopen")
    def test_upstream_down_answers_502_with_escaped_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("<script>x</script>")
        resp = self.client.get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn("<script>x", resp.text)


@unittest.skipUnless(_load_hermes_auth(), "hermes-agent is not installed")
class HermesTokenAuthTests(unittest.TestCase):
    """The plugin routes behind Hermes's real auth_middleware, as the dashboard mounts them."""

    def setUp(self):
        ws = _load_hermes_auth()
        self.token = ws._SESSION_TOKEN
        self.app = FastAPI()
        self.app.state.startup_ready = True
        self.app.middleware("http")(ws.auth_middleware)
        self.app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(self.app)

    @patch("urllib.request.urlopen")
    def test_no_session_token_is_401_and_never_reaches_upstream(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "<html><head></head></html>", "text/html")
        for path in ("/api/plugins/crew/board", "/api/plugins/crew/card/t_1", "/api/plugins/crew/card/t_1.json",
                     "/api/plugins/crew/board.json", "/api/plugins/crew/avatars/role/worker.svg"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.post("/api/plugins/crew/ack/all").status_code, 401)
        self.assertEqual(self.client.get("/api/plugins/crew/board",
                                         headers={"X-Hermes-Session-Token": "wrong"}).status_code, 401)
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_session_header_as_sent_by_authed_fetch_is_served(self, mock_urlopen):
        _mock_upstream(mock_urlopen, "<html><head></head><body></body></html>", "text/html", csp=UPSTREAM_CSP)
        resp = self.client.get("/api/plugins/crew/board", headers={"X-Hermes-Session-Token": self.token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="crew-parent-bridge"', resp.text)
        self.assertNotIn(self.token, resp.text)
        sent = dict(mock_urlopen.call_args[0][0].header_items())
        self.assertNotIn(self.token, json.dumps(sent))


class LiveUpstreamTests(unittest.TestCase):
    """The proxy against a real crew_graph_serve on a loopback port."""

    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="crew-dash-upstream-")
        cls._env = {k: os.environ.get(k) for k in ("HERMES_HOME", "CREW_ACK_FILE", "HERMES_BIN", "KANBAN_DB")}
        os.environ["HERMES_HOME"] = cls.home
        os.environ["CREW_ACK_FILE"] = os.path.join(cls.home, "crew", "attention_acks.json")
        os.environ.setdefault("HERMES_BIN", "/bin/false")
        os.environ.pop("KANBAN_DB", None)
        import crew_graph_serve
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), crew_graph_serve.Handler)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.upstream = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for k, v in cls._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        p = patch.object(plugin_api, "UPSTREAM", self.upstream)
        p.start()
        self.addCleanup(p.stop)
        app = FastAPI()
        app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(app)

    def test_ack_from_the_dashboard_origin_passes_the_same_origin_check(self):
        # The browser's own Origin/Host are the dashboard's; upstream must still see a same-origin write.
        resp = self.client.post("/api/plugins/crew/ack/all?undo=1",
                                headers={"Origin": "http://127.0.0.1:9119", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("restored", resp.text)

    def test_card_json_reaches_upstream(self):
        resp = self.client.get("/api/plugins/crew/card/t_nosuchcard.json")
        # Upstream answers for the card (no such card -> its own JSON 404), not the proxy's 400.
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.json())

    def test_healthz(self):
        resp = self.client.get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.text.startswith("ok crew board"))


if __name__ == "__main__":
    unittest.main()
