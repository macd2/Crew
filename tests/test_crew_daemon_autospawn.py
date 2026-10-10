"""Crew dashboard resilience: the plugin proxy starts crew_graph_serve on demand (no 502 after a
Hermes restart) and the desktop plugin never iframes a raw 401 JSON body."""
import importlib.util
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(__file__)
CREW_ROOT = os.path.dirname(HERE)
API_PATH = os.path.join(CREW_ROOT, "dashboard", "plugin_api.py")
PLUGIN_JS = os.path.join(CREW_ROOT, "desktop", "plugin.js")


def _load_api():
    spec = importlib.util.spec_from_file_location("crew_plugin_api_under_test", API_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _kill(pid):
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=15)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


class DaemonAutoSpawnTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = _load_api()
        except ImportError as exc:  # fastapi missing in this interpreter
            self.skipTest("plugin_api deps unavailable: %s" % exc)
        self.home = tempfile.mkdtemp(prefix="crew-autospawn-")
        self._old_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = self.home
        self.port = _free_port()
        self.api.UPSTREAM = "http://127.0.0.1:%d" % self.port

    def tearDown(self):
        _kill(self.api._last_spawn.get("pid"))
        if self._old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self._old_home
        time.sleep(0.3)
        shutil.rmtree(self.home, ignore_errors=True)

    def test_ensure_daemon_running_spawns_real_daemon(self):
        self.assertFalse(self.api._daemon_reachable())
        self.api.DAEMON_READY_TIMEOUT = 10.0
        self.assertTrue(self.api._ensure_daemon_running())
        self.assertTrue(self.api._daemon_reachable())
        self.assertIsNotNone(self.api._last_spawn["pid"])
        log = os.path.join(self.home, "logs", "crew_graph_serve.log")
        self.assertTrue(os.path.isfile(log))

    def test_proxy_route_returns_200_when_daemon_was_down(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        self.api.DAEMON_READY_TIMEOUT = 10.0
        app = FastAPI()
        app.include_router(self.api.router, prefix="/api/plugins/crew")
        resp = TestClient(app).get("/api/plugins/crew/healthz")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.text.startswith("ok"), resp.text)

    def test_running_daemon_is_not_spawned_twice(self):
        self.api.DAEMON_READY_TIMEOUT = 10.0
        self.assertTrue(self.api._ensure_daemon_running())
        first = self.api._last_spawn["pid"]
        self.assertTrue(self.api._ensure_daemon_running())
        self.assertEqual(first, self.api._last_spawn["pid"])

    def test_remote_upstream_is_never_spawned(self):
        self.api.UPSTREAM = "http://192.0.2.1:%d" % self.port   # TEST-NET-1, never routable
        self.assertFalse(self.api._ensure_daemon_running())
        self.assertIsNone(self.api._last_spawn["pid"])

    def test_autospawn_can_be_disabled(self):
        os.environ["CREW_DAEMON_AUTOSPAWN"] = "0"
        try:
            self.assertFalse(self.api._ensure_daemon_running())
            self.assertIsNone(self.api._last_spawn["pid"])
        finally:
            os.environ.pop("CREW_DAEMON_AUTOSPAWN", None)


class DesktopAuthFallbackTests(unittest.TestCase):
    def _js(self):
        with open(PLUGIN_JS, encoding="utf-8") as fh:
            return fh.read()

    def test_unauthenticated_remote_never_loads_bare_gateway_url(self):
        js = self._js()
        # The old fallback loaded '<base>/api/plugins/crew/board' with no credential -> raw 401 JSON.
        self.assertNotIn("base + '/api/plugins/crew/board'))", js)
        self.assertIn("probeLocalDaemon(1500)", js)
        self.assertIn("Authentication required: please log in to Hermes Gateway or ensure local Crew daemon is running", js)
        self.assertIn("setAuthError(AUTH_REQUIRED_MESSAGE)", js)
        self.assertIn("role: 'alert'", js)

    def test_probe_local_daemon_in_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        js = self._js()
        start = js.index("async function probeLocalDaemon(")
        fn = js[start:js.index("\n}\n", start) + 3]
        up, down = _free_port(), _free_port()
        srv = socket.socket()
        srv.bind(("127.0.0.1", up))
        srv.listen(5)
        import threading

        def serve():
            srv.settimeout(10)
            try:
                while True:
                    c, _ = srv.accept()
                    c.recv(4096)
                    c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n")
                    c.close()
            except OSError:
                pass

        threading.Thread(target=serve, daemon=True).start()
        script = ("var LOCAL_HEALTH_URL;" + fn +
                  "(async function(){var r=[];"
                  "LOCAL_HEALTH_URL='http://127.0.0.1:%d/healthz';r.push(await probeLocalDaemon(3000));"
                  "LOCAL_HEALTH_URL='http://127.0.0.1:%d/healthz';r.push(await probeLocalDaemon(3000));"
                  "console.log(JSON.stringify(r))})()" % (up, down))
        try:
            out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        finally:
            srv.close()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "[true,false]")


if __name__ == "__main__":
    unittest.main()
