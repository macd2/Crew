"""The standalone server (scripts/crew_graph_serve.py) after the switch-over: every page route is one thin shell that
loads /app.js, and the JSON routes are unchanged. A real server on a free port over a real temp kanban board."""
import http.client
import json
import os
import re
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CREW_ROOT = os.path.dirname(HERE)
for p in (HERE, CREW_ROOT, os.path.join(CREW_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from test_crew_dashboard_customization import RealBoardCase  # noqa: E402

DASH = os.path.join(CREW_ROOT, "scripts", "crew_dashboard")


class ShellServerTests(RealBoardCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import crew_graph_serve
        cls.serve = crew_graph_serve
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), crew_graph_serve.Handler)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join(5)
        super().tearDownClass()

    def req(self, path, method="GET", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, headers=headers or {})
            res = conn.getresponse()
            return res.status, {k.lower(): v for k, v in res.getheaders()}, res.read()
        finally:
            conn.close()

    def test_every_page_route_is_the_same_thin_shell(self):
        shells = set()
        for path in ("/", "/index.html", "/board", "/?all=1", "/card/" + self.card, "/card/%s/" % self.blocked):
            code, hdr, body = self.req(path)
            self.assertEqual(code, 200, path)
            self.assertTrue(hdr["content-type"].startswith("text/html"), path)
            text = body.decode("utf-8")
            self.assertIn("<div id=crew-app data-crew-shell></div>", text)
            self.assertIn("<script src=/app.js></script>", text)
            self.assertIn("<meta charset=utf-8>", text)
            self.assertIn("name=viewport", text)
            self.assertIn('rel="icon"', text)
            # nothing else: no inline script, no page markup of the old board or card
            self.assertEqual(re.findall(r"<script\b[^>]*>", text), ["<script src=/app.js>"], path)
            for old in ("page-board", "page-card", "INIT=", "<style", "id=badge"):
                self.assertNotIn(old, text, path)
            shells.add(text)
        self.assertEqual(len(shells), 1, "one shell for every route")

    def test_the_crew_card_link_serves_the_shell_and_an_unknown_card_is_a_404(self):
        _code, _hdr, board_shell = self.req("/")
        for path in ("/crew?card=" + self.card, "/crew/?card=" + self.card, "/crew"):
            code, hdr, body = self.req(path)
            self.assertEqual(code, 200, path)
            self.assertTrue(hdr["content-type"].startswith("text/html"), path)
            self.assertEqual(body, board_shell, path)
        code, _hdr, body = self.req("/crew?card=t_nosuchcard")
        self.assertEqual(code, 404)
        self.assertIn(b"no graph for t_nosuchcard", body)
        self.assertEqual(self.req("/crew?card=a%2Fb")[0], 404)

    def test_a_card_page_for_an_unknown_id_is_a_404_not_a_shell(self):
        code, hdr, body = self.req("/card/t_nosuchcard")
        self.assertEqual(code, 404)
        self.assertTrue(hdr["content-type"].startswith("text/plain"))
        self.assertIn(b"no graph for t_nosuchcard", body)
        self.assertNotIn(b"crew-app", body)

    def test_app_js_is_served_with_the_right_type_and_no_cache(self):
        code, hdr, body = self.req("/app.js")
        self.assertEqual(code, 200)
        self.assertEqual(hdr["content-type"], "text/javascript; charset=utf-8")
        self.assertEqual(hdr["cache-control"], "no-store")
        self.assertEqual(hdr["x-content-type-options"], "nosniff")
        with open(os.path.join(DASH, "app.js"), "rb") as fh:
            self.assertEqual(body, fh.read())

    def test_csp_allows_the_self_hosted_script_and_carries_no_nonce(self):
        _code, hdr, _body = self.req("/")
        csp = hdr["content-security-policy"]
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("nonce", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("connect-src 'self'", csp)
        self.assertEqual(csp, self.serve.CSP)

    def test_the_json_routes_still_answer(self):
        code, hdr, body = self.req("/board.json")
        self.assertEqual((code, hdr["content-type"]), (200, "application/json"))
        board = json.loads(body)
        self.assertIn("lanes", board)
        code, _hdr, body = self.req("/board.json?all=1&older=1")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["cards"], board["cards"] + 1)   # anchor: ?all=1 lists the PROBE card
        code, hdr, body = self.req("/card/%s.json" % self.card)
        self.assertEqual((code, hdr["content-type"]), (200, "application/json"))
        self.assertEqual(json.loads(body)["card_id"], self.card)
        code, _hdr, body = self.req("/card/t_nosuchcard.json")
        self.assertEqual(code, 404)
        self.assertIn("error", json.loads(body))
        code, hdr, _body = self.req("/avatars/role/worker.svg")
        self.assertEqual((code, hdr["content-type"]), (200, "image/svg+xml"))
        code, _hdr, body = self.req("/healthz")
        self.assertEqual(code, 200)
        self.assertTrue(body.startswith(b"ok crew board cards="))

    def test_acks_are_unchanged(self):
        self.assertEqual(self.req("/ack/all")[0], 405)
        self.assertEqual(self.req("/ack/all?undo=1", "POST")[0], 403)   # a write needs a same-origin Origin
        origin = "http://127.0.0.1:%d" % self.port
        code, _hdr, body = self.req("/ack/all?undo=1", "POST", {"Origin": origin})
        self.assertEqual(code, 200)
        self.assertIn(b"restored", body)

    def test_the_old_pages_cannot_be_served_by_accident(self):
        for name in ("board.js", "card.js", "lib.js", "crew.css", "tokens.css"):
            self.assertFalse(os.path.exists(os.path.join(DASH, name)), name)
            self.assertEqual(self.req("/" + name)[0], 404, name)
        self.assertEqual(self.req("/card/a%2Fb")[0], 404)
        self.assertEqual(self.req("/card/a/b")[0], 404)
        self.assertFalse(hasattr(self.serve, "board_page"))
        self.assertFalse(hasattr(self.serve.CG, "dashboard_asset"))

    def test_a_foreign_host_is_still_refused(self):
        code, _hdr, _body = self.req("/app.js", headers={"Host": "evil.example"})
        self.assertEqual(code, 421)


class SnapshotFileTests(RealBoardCase):
    """`crew_graph.py --html` writes one file: the app inlined plus the card as a snapshot, openable from disk."""

    def test_the_html_file_carries_the_app_and_the_card(self):
        import crew_graph_serve
        graph, err = crew_graph_serve.CG.build_graph(self.card)
        self.assertIsNone(err)
        doc = crew_graph_serve.CG.render_html(graph)
        self.assertIn('<div id="crew-app"></div>', doc)
        self.assertIn("window.__CREW_SNAPSHOT=", doc)
        self.assertIn(self.card, doc)
        with open(os.path.join(DASH, "app.js"), encoding="utf-8") as fh:
            self.assertIn(fh.read(), doc)
        self.assertEqual(len(re.findall(r"</script>", doc)), 2)   # the snapshot and the app, nothing a card can add
        markup = re.sub(r"<script>.*?</script>", "", doc, flags=re.S)   # what is left loads nothing from outside
        self.assertNotRegex(markup, r"(?:src|href)=[\"']?https?:")
        self.assertNotIn("<script src", markup)


if __name__ == "__main__":
    unittest.main()
