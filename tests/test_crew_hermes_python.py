"""crew_card.hermes_python(): committed venv first, then the legacy venv/.venv, then "". Fake roots only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import crew_card  # noqa: E402


def _py(venv):
    p = Path(venv) / "bin" / "python"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    return str(p)


class HermesPythonOrder(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "hermes-agent"
        self.root.mkdir()
        self._mods = {k: sys.modules.pop(k) for k in list(sys.modules) if k == "pm" or k.startswith("pm.")}

    def tearDown(self):
        for k in [k for k in sys.modules if k == "pm" or k.startswith("pm.")]:
            del sys.modules[k]
        sys.modules.update(self._mods)
        self._tmp.cleanup()

    def _fake_pm(self, body):
        d = self.root / "pm"
        d.mkdir()
        (d / "__init__.py").write_text("")
        (d / "environments.py").write_text(body)

    def test_committed_venv_wins_over_legacy(self):
        committed = Path(self._tmp.name) / "store" / "venv"
        want = _py(committed)
        _py(self.root / "venv")
        self._fake_pm("def committed_venv(root):\n    return %r\n" % str(committed))
        self.assertEqual(want, crew_card.hermes_python(str(self.root)))
        self.assertNotIn(str(self.root), sys.path)

    def test_no_pm_falls_back_to_legacy_venv(self):
        want = _py(self.root / "venv")
        self.assertEqual(want, crew_card.hermes_python(str(self.root)))

    def test_dot_venv_also_found(self):
        want = _py(self.root / ".venv")
        self.assertEqual(want, crew_card.hermes_python(str(self.root)))

    def test_committed_venv_none_or_raising_falls_through(self):
        self._fake_pm("def committed_venv(root):\n    return None\n")
        self.assertEqual("", crew_card.hermes_python(str(self.root)))
        for k in [k for k in sys.modules if k == "pm" or k.startswith("pm.")]:
            del sys.modules[k]
        (self.root / "pm" / "environments.py").write_text("def committed_venv(root):\n    raise RuntimeError('x')\n")
        want = _py(self.root / "venv")
        self.assertEqual(want, crew_card.hermes_python(str(self.root)))

    def test_nothing_found_is_empty(self):
        self.assertEqual("", crew_card.hermes_python(str(self.root)))


if __name__ == "__main__":
    unittest.main()
