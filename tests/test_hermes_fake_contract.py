"""The fake Hermes (hermes_fake.py) must print exactly what the real `hermes config get` prints.

Why this exists: the installer was tested only against a fake that printed scalars and flat lists, so a list of
mappings (fallback_providers) re-applied on every install and nothing failed (PR #25). A test double that only
models what the code already handles can never find the case the code forgot. Two checks keep it honest:
  1. the fake reproduces every captured real shape (tests/fixtures/hermes_config_get.json);
  2. when a real `hermes` is on PATH, the captured shapes still match it (drift detector; skipped otherwise).
A new value shape the installer reads or writes = a new row in the fixture, captured with --refresh.
"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "hermes_config_get.json"
sys.path.insert(0, str(HERE))
from hermes_fake import FakeConfig  # noqa: E402
sys.path.insert(0, str(HERE.parent))
import install  # noqa: E402


def _shapes():
    return json.loads(FIXTURE.read_text())["shapes"]


def _real(literal, hermes):
    """What a real Hermes prints for `config get` after `config set` of this literal, in a throwaway HERMES_HOME."""
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, HERMES_HOME=home)
        subprocess.run([hermes, "config", "set", "contract.k", literal], env=env, capture_output=True, text=True, timeout=60)
        p = subprocess.run([hermes, "config", "get", "contract.k"], env=env, capture_output=True, text=True, timeout=60)
    out = "".join(l + "\n" for l in p.stdout.splitlines() if "Bitwarden" not in l)
    return p.returncode, out


class FakeMatchesRealHermes(unittest.TestCase):
    def test_fake_reproduces_every_captured_shape(self):
        for s in _shapes():
            with self.subTest(shape=s["name"]):
                fake = FakeConfig()
                fake("p", "config", "set", "k", s["set"])
                r = fake("p", "config", "get", "k")
                self.assertEqual((s["rc"], s["stdout"]), (r.returncode, r.stdout))

    def test_fake_reports_an_unset_key_as_exit_1(self):
        self.assertEqual(1, FakeConfig()("p", "config", "get", "nope").returncode)

    @unittest.skipUnless(shutil.which("hermes"), "no real hermes on PATH")
    def test_captured_shapes_still_match_a_real_hermes(self):
        # Drift is judged by what the installer READS, not by bytes: Hermes versions differ in block-list indent
        # (`  - a` on one, `- a` on upstream main, 2026-11-14 CI), and the installer reads both the same. A real
        # change of shape (a list printed as JSON, a mapping flattened) still reads differently and fails here.
        hermes = shutil.which("hermes")
        for s in _shapes():
            with self.subTest(shape=s["name"]):
                rc, out = _real(s["set"], hermes)
                self.assertEqual(s["rc"], rc)
                self.assertEqual(install._parse_get(s["stdout"]), install._parse_get(out), out)

    def test_block_list_indent_reads_the_same(self):
        for flush, indented in (("- a\n- b\n", "  - a\n  - b\n"),
                                ("- provider: p\n  model: m\n", "  - provider: p\n    model: m\n")):
            with self.subTest(shape=flush):
                self.assertEqual(install._parse_get(flush), install._parse_get(indented))
                self.assertIsNotNone(install._parse_get(flush))


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        data = json.loads(FIXTURE.read_text())
        for s in data["shapes"]:
            s["rc"], s["stdout"] = _real(s["set"], shutil.which("hermes"))
        FIXTURE.write_text(json.dumps(data, indent=2) + "\n")
        print("refreshed", FIXTURE)
    else:
        unittest.main()
