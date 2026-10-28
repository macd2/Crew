"""The gateway (it runs the kanban dispatcher) is not running: crew_card.dispatcher_state reads gateway.pid and the
gateway_state.json heartbeat, and the /crew card-open preload, board.json and /crew-diagnose each name it."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_card  # noqa: E402
import crew_diagnose  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GatewayHome(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-gw-test-")
        os.environ["HERMES_HOME"] = self.home
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(self.restore)

    def restore(self):
        for k in [k for k in os.environ if k not in self._env]:
            del os.environ[k]
        os.environ.update(self._env)

    def pid_file(self, text):
        Path(self.home, "gateway.pid").write_text(text, encoding="utf-8")

    def beat(self, seconds_ago):
        when = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
        Path(self.home, "gateway_state.json").write_text(json.dumps({"updated_at": when.isoformat()}), encoding="utf-8")

    def dead_pid(self):
        p = subprocess.Popen([sys.executable, "-c", "pass"])
        p.wait()
        return p.pid


class DispatcherState(GatewayHome):
    def test_missing_pid_file_is_not_alive(self):
        st = crew_card.dispatcher_state()
        self.assertFalse(st["alive"])
        self.assertIn("no gateway.pid", st["detail"])
        self.assertIn("hermes gateway run", st["command"])
        self.assertIn("hermes gateway install", st["command"])

    def test_dead_pid_is_not_alive(self):
        pid = self.dead_pid()
        self.pid_file(json.dumps({"pid": pid, "kind": "hermes-gateway"}))
        st = crew_card.dispatcher_state()
        self.assertFalse(st["alive"])
        self.assertIn("pid %d" % pid, st["detail"])

    def test_live_pid_json_and_bare_forms_are_alive(self):
        for text in (json.dumps({"pid": os.getpid()}), str(os.getpid())):
            self.pid_file(text)
            self.beat(5)
            st = crew_card.dispatcher_state()
            self.assertTrue(st["alive"], text)
            self.assertEqual("", st["command"])

    def test_live_pid_without_a_state_file_is_alive(self):
        self.pid_file(str(os.getpid()))
        self.assertTrue(crew_card.dispatcher_state()["alive"])

    def test_live_pid_with_a_stale_heartbeat_reads_frozen(self):
        self.pid_file(str(os.getpid()))
        self.beat(crew_card.GATEWAY_HEARTBEAT_STALE_S + 60)
        st = crew_card.dispatcher_state()
        self.assertFalse(st["alive"])
        self.assertIn("frozen", st["detail"])
        self.assertIn("hermes gateway restart", st["command"])

    def test_garbage_files_never_raise(self):
        for text in ("", "not json", "{}", '{"pid": "x"}', "-3"):
            self.pid_file(text)
            self.assertFalse(crew_card.dispatcher_state()["alive"], text)
        self.pid_file(str(os.getpid()))
        Path(self.home, "gateway_state.json").write_text("{broken", encoding="utf-8")
        self.assertTrue(crew_card.dispatcher_state()["alive"])

    def test_a_profile_home_reads_the_base_home_files(self):
        base = Path(self.home)
        prof = base / "profiles" / "crew-worker"
        prof.mkdir(parents=True)
        os.environ["HERMES_HOME"] = str(prof)
        (base / "gateway.pid").write_text(str(os.getpid()), encoding="utf-8")
        self.assertTrue(crew_card.dispatcher_state()["alive"])

    def test_the_warning_names_the_command_and_is_empty_when_alive(self):
        text = crew_card.dispatcher_warning()
        self.assertIn("does not start until it runs", text)
        self.assertIn("hermes gateway run", text)
        self.pid_file(str(os.getpid()))
        self.assertEqual("", crew_card.dispatcher_warning())


class IntakeLine(GatewayHome):
    def plugin(self):
        return load(str(REPO / "__init__.py"), "crew_gw_plugin")

    def test_the_card_open_preload_carries_the_line_when_down(self):
        ctx = self.plugin().crew_intake_preload(user_message="/crew make it fast", session_id="GW1", turn_id="T")["context"]
        self.assertIn("The Hermes gateway is not running", ctx)
        self.assertIn("hermes gateway install", ctx)

    def test_the_gateway_line_comes_before_the_last_line_link(self):
        os.environ["CREW_DASHBOARD_URL"] = "https://crew.example.test"
        try:
            ctx = self.plugin().crew_intake_preload(user_message="/crew make it fast", session_id="GW3", turn_id="T", platform="cli")["context"]
        finally:
            os.environ.pop("CREW_DASHBOARD_URL", None)
        self.assertIn("The Hermes gateway is not running", ctx)
        self.assertIn("Crew Dashboard: https://crew.example.test/crew?card=<id>", ctx)
        self.assertIn("before the last line", ctx)

    def test_in_desktop_the_gateway_line_ends_the_reply_under_the_linked_lead(self):
        os.environ["CREW_DASHBOARD_URL"] = "https://crew.example.test"
        try:
            ctx = self.plugin().crew_intake_preload(user_message="/crew make it fast", session_id="GW4", turn_id="T", platform="desktop")["context"]
        finally:
            os.environ.pop("CREW_DASHBOARD_URL", None)
        self.assertIn("The Hermes gateway is not running", ctx)
        self.assertIn("**Card open** · [<id>](https://crew.example.test/crew?card=<id>) · <title>", ctx)
        self.assertIn("as its last line", ctx)
        self.assertNotIn("Open it in Crew", ctx)

    def test_no_line_when_the_gateway_runs(self):
        self.pid_file(str(os.getpid()))
        ctx = self.plugin().crew_intake_preload(user_message="/crew make it fast", session_id="GW2", turn_id="T")["context"]
        self.assertNotIn("The Hermes gateway is not running", ctx)

    def test_the_skill_tells_the_model_to_say_it(self):
        text = (REPO / "skills" / "crew" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("preload says the gateway is not running", text)


class DiagnoseLine(GatewayHome):
    def test_first_line_when_down_even_with_no_cards(self):
        out = crew_diagnose.render([], "ready", None, crew_card.dispatcher_warning())
        first = out.splitlines()[0]
        self.assertTrue(first.startswith("WARNING: The gateway is not running"), first)
        self.assertIn("diagnose: 0 card(s) in state ready", out)

    def test_no_line_when_alive_or_no_warning(self):
        self.assertEqual("diagnose: 0 card(s) in state ready", crew_diagnose.render([], "ready", None))


class BoardField(GatewayHome):
    def test_board_data_carries_the_dispatcher(self):
        from tests import kernel_board as kbd
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        _kb, conn, path = kbd.open_board(tmp.name)
        self.addCleanup(conn.close)
        os.environ["KANBAN_DB"] = path
        mod = load(str(REPO / "scripts" / "crew_graph_serve.py"), "cgs_gw")
        down = mod.board_data()["dispatcher"]
        self.assertFalse(down["alive"])
        self.assertIn("hermes gateway", down["command"])
        self.pid_file(str(os.getpid()))
        self.assertTrue(json.loads(mod.board_json())["dispatcher"]["alive"])


if __name__ == "__main__":
    unittest.main()
