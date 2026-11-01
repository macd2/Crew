"""The installer, run for real against a real Hermes, must converge: install, install again, and nothing is left to change.

Why: fakes only know the value shapes their author thought of (PR #25: a list of mappings re-applied on every install and every
test passed). This test uses NO fake: a throwaway HOME (so `hermes -p <role>` and the profile folders are the scratch ones, never
the real ones), the real `hermes` that writes and reads the config, the real install.py, and an owner override that carries
every value shape an owner key can hold. Whatever Hermes reads back in another form than the installer wrote it fails here -
nobody has to think of the case first.

Slow (about 4-5 minutes per test: every `hermes` call starts a real process), so it runs in CI, in the nightly proofs and on
demand, not on every push. Opt-in: CREW_REAL_HERMES=1 and a real hermes on PATH, otherwise skipped (the plain suite stays fast). Run it:
    CREW_REAL_HERMES=1 python -m pytest tests/test_installer_converges_real_hermes.py -q
The `installer-converges` CI job runs it on every pull request. Never test an install that was cut off
halfway: it leaves state that needs a second run, and that is not a bug.
"""
import os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERMES = shutil.which("hermes")

# every shape an owner key can hold (model.*, agent.max_turns, fallback_providers): string, number, list of mappings
OVERRIDE = """\
model.default = converge-model
agent.max_turns = 77
fallback_providers = [{"provider":"litellm","model":"reason"},{"provider":"p2","model":"m2","base_url":"https://example.invalid/v1"}]
"""


class Box:
    """One throwaway home. The real hermes source is linked in; everything it writes lands in the scratch."""
    def __init__(self):
        self.home = tempfile.mkdtemp(prefix="crew-converge-")
        hh = os.path.join(self.home, ".hermes")
        os.makedirs(os.path.join(hh, "crew", "templates", "worker"))
        Path(hh, "crew", "templates", "worker", "settings.conf").write_text(OVERRIDE)
        src = os.environ.get("HERMES_AGENT_DIR") or os.path.expanduser("~/.hermes/hermes-agent")
        if os.path.isdir(src):
            os.symlink(src, os.path.join(hh, "hermes-agent"))

    def run(self, *args):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "HERMES_HOME")}
        env.update(HOME=self.home, HERMES_BIN=HERMES, TMPDIR=self.home)
        return subprocess.run([sys.executable, str(REPO / "install.py"), "--no-service", "--no-cron", *args],
                              env=env, capture_output=True, text=True, timeout=900, cwd=str(REPO))

    def clean(self):
        shutil.rmtree(self.home, ignore_errors=True)


@unittest.skipUnless(HERMES and os.environ.get("CREW_REAL_HERMES") == "1",
                     "slow real-Hermes test: set CREW_REAL_HERMES=1 (needs a real hermes on PATH)")
class InstallerConvergesOnRealHermes(unittest.TestCase):
    def setUp(self):
        self.box = Box()
        self.addCleanup(self.box.clean)

    def _check_clean(self, why):
        out = self.box.run("--check").stdout
        self.assertIn("nothing to change", out, "%s:\n%s" % (why, out[-2000:]))

    def test_install_twice_leaves_nothing_to_change(self):
        for n in (1, 2):
            r = self.box.run()
            self.assertEqual(0, r.returncode, "install %d failed:\n%s" % (n, (r.stdout + r.stderr)[-1500:]))
        self._check_clean("after two installs --check must be clean")

    def test_a_fresh_install_is_complete_in_one_run(self):
        r = self.box.run()
        self.assertEqual(0, r.returncode, (r.stdout + r.stderr)[-1500:])
        self._check_clean("one install must be enough")


if __name__ == "__main__":
    unittest.main()
