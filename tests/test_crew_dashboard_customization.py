import html
import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

HERE = os.path.dirname(__file__)
CREW_ROOT = os.path.dirname(HERE)

# Ensure crew root is in path so dashboard.plugin_api can be imported
import sys
if CREW_ROOT not in sys.path:
    sys.path.insert(0, CREW_ROOT)

from dashboard.plugin_api import (
    router,
    _sanitize_color,
    _public_crew_url,
    _CARD_ID_RE,
    _ACK_PATH_RE,
    _AVATAR_PATH_RE,
)


class CrewDashboardCustomizationTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/plugins/crew")
        self.client = TestClient(self.app)

    def test_manifest_metadata(self):
        manifest_path = os.path.join(CREW_ROOT, "dashboard", "manifest.json")
        self.assertTrue(os.path.isfile(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("name"), "crew")
        self.assertEqual(data.get("version"), "0.8.1")
        self.assertEqual(data.get("tab", {}).get("path"), "/crew")
        self.assertEqual(data.get("entry"), "dist/index.js")
        self.assertEqual(data.get("api"), "plugin_api.py")

    def test_dist_index_js_authed_fetch_and_srcdoc(self):
        dist_path = os.path.join(CREW_ROOT, "dashboard", "dist", "index.js")
        self.assertTrue(os.path.isfile(dist_path))
        with open(dist_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hand-written React component", content)
        self.assertIn("authedFetch", content)
        self.assertIn("srcDoc", content)
        # Ensure session tokens are never referenced in frontend code
        self.assertNotIn("_SESSION_TOKEN", content)

    def test_color_sanitization_rejects_xss(self):
        # Valid colors
        self.assertEqual(_sanitize_color("#041c1c"), "#041c1c")
        self.assertEqual(_sanitize_color("#fff"), "#fff")
        self.assertEqual(_sanitize_color("#AABBCC"), "#aabbcc")

        # Reflected XSS injection attempts must be dropped
        self.assertIsNone(_sanitize_color("</style><script>alert(1)</script>"))
        self.assertIsNone(_sanitize_color("#041c1c; alert(1)"))
        self.assertIsNone(_sanitize_color("red; background: blue"))
        self.assertIsNone(_sanitize_color("expression(alert(1))"))
        self.assertIsNone(_sanitize_color("rgba(0,0,0,1)"))

    def test_public_crew_url_sanitization(self):
        # Normal request
        mock_req = MagicMock()
        mock_req.headers = {"host": "agent.example.com", "x-forwarded-proto": "https"}
        mock_req.url.scheme = "https"
        url = _public_crew_url(mock_req)
        self.assertEqual(url, "https://agent.example.com/api/plugins/crew/board")

        # Hostile Host injection must fallback safely without HTML/attribute breakout
        mock_hostile = MagicMock()
        mock_hostile.headers = {
            "host": 'attacker.com" onclick="alert(1)',
            "x-forwarded-proto": "javascript:alert(1)",
        }
        mock_hostile.url.scheme = "http"
        safe_url = _public_crew_url(mock_hostile)
        self.assertNotIn('"', safe_url)
        self.assertNotIn("javascript", safe_url)
        self.assertEqual(safe_url, "http://127.0.0.1:9119/api/plugins/crew/board")

    def test_route_allowlisting_and_validation(self):
        # Card ID regex validation
        self.assertTrue(_CARD_ID_RE.match("t_12345"))
        self.assertTrue(_CARD_ID_RE.match("card-abc_12"))
        self.assertFalse(_CARD_ID_RE.match("../../etc/passwd"))
        self.assertFalse(_CARD_ID_RE.match("card/subpath"))

        # Ack action validation
        self.assertTrue(_ACK_PATH_RE.match("all"))
        self.assertTrue(_ACK_PATH_RE.match("t_12345"))
        self.assertFalse(_ACK_PATH_RE.match("all/extra"))

        # Avatar path validation
        self.assertTrue(_AVATAR_PATH_RE.match("role/worker.svg"))
        self.assertTrue(_AVATAR_PATH_RE.match("role/verifier.png"))
        self.assertFalse(_AVATAR_PATH_RE.match("../secret.txt"))
        self.assertFalse(_AVATAR_PATH_RE.match("role/worker.exe"))

    @patch("urllib.request.urlopen")
    def test_board_proxy_transforms_and_security(self, mock_urlopen):
        raw_upstream_html = (
            "<!doctype html><html><head><title>Crew</title></head><body>"
            "<a class=tailnet href='http://127.0.0.1:8799/'>link</a>"
            '<a href="/card/t_123">Task</a>'
            '<a class="brand" href="/">Crew</a>'
            '<img src="/avatars/role/worker.svg">'
            "</body></html>"
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = raw_upstream_html.encode("utf-8")
        mock_resp.status = 200
        mock_resp.headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Content-Security-Policy": "default-src 'self'",
        }
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Request board with potentially hostile query param
        resp = self.client.get(
            "/api/plugins/crew/board?bg=%3C/style%3E%3Cscript%3Ealert(1)%3C/script%3E",
            headers={"Host": "127.0.0.1:9119"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-security-policy"), "default-src 'self'")
        # Ensure session tokens are never leaked into body or cookies
        self.assertNotIn("_SESSION_TOKEN", resp.text)
        self.assertNotIn("set-cookie", resp.headers)

        # Ensure reflected XSS was neutralized
        self.assertNotIn("alert(1)", resp.text)

        # Ensure link loop fix is present with target=_blank
        self.assertIn('target="_blank"', resp.text)
        self.assertIn("open in new tab ↗", resp.text)

        # Ensure base href and bridge are injected
        self.assertIn('<base href="/api/plugins/crew/">', resp.text)
        self.assertIn('id="crew-parent-bridge"', resp.text)

        # Ensure absolute avatar path is rewritten for relative base
        self.assertIn('avatars/role/worker.svg', resp.text)
        self.assertNotIn('"/avatars/role/worker.svg"', resp.text)

    @patch("urllib.request.urlopen")
    def test_ack_post_forwards_upstream_origin_and_host(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        resp = self.client.post("/api/plugins/crew/ack/all", content=b"")
        self.assertEqual(resp.status_code, 200)

        # Verify urllib.request.Request called with Host and Origin matching upstream
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_header("Host"), "127.0.0.1:8799")
        self.assertEqual(req.get_header("Origin"), "http://127.0.0.1:8799")


if __name__ == "__main__":
    unittest.main()
