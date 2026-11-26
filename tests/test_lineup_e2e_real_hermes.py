"""Lineups end to end, against a real Hermes: the owner's flow, no fakes.

A throwaway HOME (so every `hermes -p ...` and profile folder is the scratch one), the real `hermes`, the real install.py and
the INSTALLED plugin copy:

  1. install the shipped crew
  2. `/crew --lineup security <ask>` through the installed plugin's own intake hook: the ask comes back without the flag,
     the facts name the lineup being set up, and the installer starts in the background
  3. the background install finishes (<crew>/lineup.json ready); one profile per lineup role, each with its role, its
     generated role skill and the lineup's roles.json; the plugin in a role profile treats the new roles as the writers
  4. a card for a lineup role passes the contract, a card for `worker` is refused, `--check` has nothing to change
  5. `install.py --uninstall-lineup security` removes the lineup's profiles and gives the shipped crew back; the
     lineup file stays

Slow (every `hermes` call is a real process). Opt-in like the converge test:
    CREW_REAL_HERMES=1 python -m pytest tests/test_lineup_e2e_real_hermes.py -q
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERMES = shutil.which("hermes")
ROLES = ["auditor", "remediator", "hardener"]

# Runs inside the scratch HOME with the plugin copy the installer put in a profile: what Hermes itself would load.
PROBE = r'''
import importlib.util, json, os, sys
plugin = sys.argv[1]
spec = importlib.util.spec_from_file_location("crew_plugin_e2e", os.path.join(plugin, "__init__.py"),
                                              submodule_search_locations=[plugin])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = {}
if sys.argv[2] == "intake":
    ctx = mod.crew_intake_preload(user_message="/crew --lineup security audit the login flow of /srv/app",
                                  session_id="e2e-session", turn_id="t1", platform="cli") or {}
    out["context"] = ctx.get("context", "")
    out["brief"] = mod._CREW_BRIEFS.get("e2e-session")
else:
    tool = mod._card_tool()
    out["writers"] = list(tool.writer_roles())
    out["all"] = list(tool.all_roles())
    out["task_class"] = tool.role_task_class("auditor")
    out["facts"] = mod._intake_facts()
    body = ("Role: %s\nBudget: 500000\nRoute: none\nGOAL: Audit the login form\nArtifact: a report\n"
            "Lands at: /srv/report.md\nFor: the owner\nConstraints: none stated\nDone when: the report exists\n"
            "proof command: test -s /srv/report.md\n")
    out["gaps_auditor"] = tool.contract_gaps(tool.parse_contract(body % "auditor")) \
        if hasattr(tool, "parse_contract") else None
    out["gaps_worker"] = tool.contract_gaps(tool.parse_contract(body % "worker")) \
        if hasattr(tool, "parse_contract") else None
print(json.dumps(out, default=str))
'''


class Box:
    def __init__(self):
        self.home = tempfile.mkdtemp(prefix="crew-lineup-e2e-")
        self.hh = os.path.join(self.home, ".hermes")
        os.makedirs(self.hh)
        src = os.environ.get("HERMES_AGENT_DIR") or os.path.expanduser("~/.hermes/hermes-agent")
        if os.path.isdir(src):
            os.symlink(src, os.path.join(self.hh, "hermes-agent"))

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "HERMES_HOME") and not k.startswith("CREW_")}
        env.update(HOME=self.home, HERMES_BIN=HERMES, TMPDIR=self.home, **extra)
        return env

    def install(self, *args):
        return subprocess.run([sys.executable, str(REPO / "install.py"), "--no-service", "--no-cron", *args],
                              env=self.env(), capture_output=True, text=True, timeout=1800, cwd=str(REPO))

    def hermes(self, profile, *args):
        return subprocess.run([HERMES, "-p", profile, *args], env=self.env(), capture_output=True, text=True,
                              timeout=120)

    def probe(self, home, what):
        plugin = os.path.join(home, "plugins", "crew")
        r = subprocess.run([sys.executable, "-c", PROBE, plugin, what], env=self.env(HERMES_HOME=home),
                           capture_output=True, text=True, timeout=300, cwd=self.home)
        if r.returncode != 0:
            raise AssertionError("probe %s failed:\n%s" % (what, (r.stdout + r.stderr)[-3000:]))
        return json.loads(r.stdout.strip().splitlines()[-1])

    def profile_home(self, name):
        return os.path.join(self.hh, "profiles", name)

    def state(self):
        try:
            with open(os.path.join(self.hh, "crew", "lineup.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def log(self):
        try:
            return Path(self.hh, "crew", "lineup-install.log").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def clean(self):
        shutil.rmtree(self.home, ignore_errors=True)


@unittest.skipUnless(HERMES and os.environ.get("CREW_REAL_HERMES") == "1",
                     "slow real-Hermes test: set CREW_REAL_HERMES=1 (needs a real hermes on PATH)")
class LineupEndToEnd(unittest.TestCase):
    def setUp(self):
        self.box = Box()
        self.addCleanup(self.box.clean)

    def owner_setup(self):
        """The owner profile (default) declares a hooks section, two MCP servers, a credential and a non-crew skill, so
        the inherit defaults are visible: a role gets the hooks and the credential, and none of the servers or the
        skill. The hooks section holds settings, not a command, so no consent prompt is involved."""
        box = self.box
        for key, val in (("hooks", json.dumps({"output_spill": {"max_chars": 12345}})),
                         ("mcp_servers", json.dumps({"alpha": {"command": "/bin/true"},
                                                     "beta": {"url": "http://127.0.0.1:9/mcp"}}))):
            r = box.hermes("default", "config", "set", "--force", key, val)
            self.assertEqual(0, r.returncode, (r.stdout + r.stderr)[-1000:])
        with open(os.path.join(box.hh, ".env"), "a", encoding="utf-8") as fh:
            fh.write("CREW_E2E_KEY=owner-credential\n")
        skill = Path(box.hh, "skills", "devops", "owner-only-skill", "SKILL.md")
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("---\nname: owner-only-skill\ndescription: x\n---\nx\n", encoding="utf-8")

    def sets_setup(self):
        """A second profile `e2e-src` with one skill and one MCP server, and the owner's copy of the security lineup
        edited so two roles use the set forms: auditor the object form (the owner's set, plus one from e2e-src, minus
        one), remediator a list with a bare (owner) item and a profile/name item. hardener keeps the defaults."""
        box = self.box
        r = box.hermes("default", "profile", "create", "e2e-src", "--no-skills")
        self.assertEqual(0, r.returncode, (r.stdout + r.stderr)[-1000:])
        r = box.hermes("e2e-src", "config", "set", "--force", "mcp_servers", json.dumps({"gamma": {"command": "/bin/false"}}))
        self.assertEqual(0, r.returncode, (r.stdout + r.stderr)[-1000:])
        skill = Path(box.profile_home("e2e-src"), "skills", "tools", "src-skill", "SKILL.md")
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("---\nname: src-skill\ndescription: x\n---\nx\n", encoding="utf-8")
        recipe = Path(box.hh, "crew", "lineups", "security.json")
        data = json.loads(recipe.read_text(encoding="utf-8"))
        for role in data["roles"]:
            if role["name"] == "auditor":
                role["inherit"] = {
                    "skills": {"from": "owner", "add": ["e2e-src/src-skill"], "drop": ["owner-only-skill"]},
                    "mcp": {"from": "owner", "add": ["e2e-src/gamma"], "drop": ["beta"]}}
            elif role["name"] == "remediator":
                role["inherit"] = {"skills": ["owner-only-skill", "e2e-src/src-skill"], "mcp": ["beta", "e2e-src/gamma"]}
        recipe.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def skill_names(self, home):
        """Skill names of a profile (folder names holding a SKILL.md), crew's own and Hermes's essential left out."""
        root = Path(home, "skills")
        return sorted({p.parent.name for p in root.rglob("SKILL.md")
                       if not p.relative_to(root).parts[0] in ("crew",) and not any(x.startswith(".") for x in
                                                                                     p.relative_to(root).parts)}
                      - {"hermes-agent"})

    def assert_sets(self):
        box = self.box
        owner = self.skill_names(box.hh)
        self.assertIn("owner-only-skill", owner)
        aud, rem = box.profile_home("crew-auditor"), box.profile_home("crew-remediator")
        self.assertEqual(sorted((set(owner) - {"owner-only-skill"}) | {"src-skill"}), self.skill_names(aud),
                         "auditor: the owner's skills minus owner-only-skill plus e2e-src/src-skill")
        self.assertEqual({"alpha": {"command": "/bin/true"}, "gamma": {"command": "/bin/false"}},
                         self.section(aud, "mcp_servers"))
        self.assertEqual(["owner-only-skill", "src-skill"], self.skill_names(rem), "remediator: exactly the list")
        self.assertEqual({"beta": {"url": "http://127.0.0.1:9/mcp"}, "gamma": {"command": "/bin/false"}},
                         self.section(rem, "mcp_servers"))

    def section(self, home, key):
        import yaml
        with open(os.path.join(home, "config.yaml"), encoding="utf-8") as fh:
            return (yaml.safe_load(fh) or {}).get(key)

    def assert_inherit_defaults(self, profile):
        home = self.box.profile_home(profile)
        self.assertFalse(self.section(home, "mcp_servers"), "%s: no MCP servers by default" % profile)
        self.assertEqual(12345, ((self.section(home, "hooks") or {}).get("output_spill") or {}).get("max_chars"),
                         "%s: the owner's hooks" % profile)
        self.assertIn("CREW_E2E_KEY=owner-credential", Path(home, ".env").read_text(encoding="utf-8"),
                      "%s: the owner's credentials" % profile)
        skills = sorted(p.relative_to(Path(home, "skills")).parent.as_posix()
                        for p in Path(home, "skills").rglob("SKILL.md"))
        extra = [s for s in skills if not s.startswith("crew/") and s != "autonomous-ai-agents/hermes-agent"]
        self.assertEqual([], extra, "%s: crew skills only by default" % profile)

    def test_the_owners_lineup_flow(self):
        box = self.box
        self.owner_setup()
        t0 = time.time()
        # 1. the shipped crew
        r = box.install()
        self.assertEqual(0, r.returncode, "default install failed:\n%s" % (r.stdout + r.stderr)[-2000:])
        for role in ("coordinator", "worker", "content", "verifier"):
            self.assertTrue(os.path.isdir(box.profile_home("crew-" + role)), role)
            self.assert_inherit_defaults("crew-" + role)
        print("\n[e2e] shipped crew installed in %.0fs" % (time.time() - t0))
        self.sets_setup()

        # 2. /crew --lineup security <ask>, through the installed plugin's intake hook
        out = box.probe(box.hh, "intake")
        self.assertNotIn("--lineup", out["brief"] or "", "the flag must not reach the ask")
        self.assertIn("audit the login flow", out["brief"] or "")
        self.assertIn("security", out["context"])
        for role in ROLES:
            self.assertIn(role, out["context"], "the facts name the lineup's roles while it is set up")

        # 3. the background install converges
        deadline = time.time() + 1500
        while time.time() < deadline:
            st = box.state()
            if st.get("status") in ("ready", "failed") and st.get("active") == "security":
                break
            time.sleep(5)
        st = box.state()
        self.assertEqual("ready", st.get("status"), "background install: %s\nlog:\n%s" % (st, box.log()[-3000:]))
        self.assertEqual(ROLES, st.get("roles"))
        self.assertEqual("security", box.hermes("default", "config", "get", "crew.lineup").stdout.strip())

        for role in ROLES:
            home = box.profile_home("crew-" + role)
            self.assertTrue(os.path.isdir(home), "crew-%s missing\n%s" % (role, box.log()[-3000:]))
            self.assertEqual(role, box.hermes("crew-" + role, "config", "get", "crew.role").stdout.strip())
            skill = Path(home, "skills", "crew", "crew-role-%s" % role, "SKILL.md")
            self.assertTrue(skill.is_file(), skill)
            text = skill.read_text(encoding="utf-8")
            self.assertIn("name: crew-role-%s" % role, text)
            self.assertIn(".crew/", text, "crew's writer rules are always part of the role skill")
            roles = json.loads(Path(home, "roles", "crew", "roles.json").read_text(encoding="utf-8"))
            writers = [x["name"] for x in roles["roles"] if x.get("kind") == "writer"]
            self.assertEqual(ROLES, writers)
            self.assertTrue(Path(home, "SOUL.md").read_text(encoding="utf-8").strip())
        for role in ("worker", "content"):
            self.assertFalse(os.path.isdir(box.profile_home("crew-" + role)),
                             "crew-%s is not in the lineup and has no open cards: removed" % role)
        self.assert_inherit_defaults("crew-hardener")
        self.assert_sets()
        print("[e2e] lineup installed with the set forms at %.0fs" % (time.time() - t0))
        auditor_skill = Path(box.profile_home("crew-auditor"), "skills", "crew", "crew-role-auditor", "SKILL.md")
        self.assertIn("never", auditor_skill.read_text(encoding="utf-8").lower())

        # the plugin in a lineup role profile and in the owner profile sees the lineup's writers
        for home in (box.hh, box.profile_home("crew-auditor")):
            seen = box.probe(home, "runtime")
            self.assertEqual(ROLES, seen["writers"], home)
            self.assertEqual(["coordinator"] + ROLES + ["verifier"], seen["all"])
            self.assertEqual("review", seen["task_class"])
            for role in ROLES:
                self.assertIn(role, seen["facts"])
            if seen["gaps_auditor"] is not None:
                self.assertFalse([g for g in seen["gaps_auditor"] if g.startswith("role")], seen["gaps_auditor"])
                self.assertTrue([g for g in seen["gaps_worker"] if g.startswith("role")], seen["gaps_worker"])

        # 4. converged: nothing left to change
        r = box.install("--check")
        self.assertIn("nothing to change", r.stdout, r.stdout[-3000:])
        self.assert_sets()

        # 5. uninstall the lineup (the reverse of installing it): its profiles go entirely, the shipped writers come
        # back, and the lineup file - the recipe - stays where it is
        recipe = Path(box.hh, "crew", "lineups", "security.json")
        self.assertTrue(recipe.is_file(), "the shipped lineups land in <crew>/lineups/")
        before = recipe.read_bytes()
        r = box.install("--uninstall-lineup", "security")
        self.assertEqual(0, r.returncode, (r.stdout + r.stderr)[-3000:])
        self.assertIn("lineup security uninstalled", r.stdout)
        self.assertEqual(before, recipe.read_bytes())
        self.assertFalse(Path(box.hh, "crew", "lineup-build", "security").exists())
        self.assertEqual("default", box.hermes("default", "config", "get", "crew.lineup").stdout.strip())
        for role in ROLES:
            self.assertFalse(os.path.isdir(box.profile_home("crew-" + role)), "crew-%s left behind" % role)
        for role in ("worker", "content"):
            self.assertTrue(os.path.isdir(box.profile_home("crew-" + role)))
        self.assertEqual(["worker", "content"], box.probe(box.hh, "runtime")["writers"])
        r = box.install("--check")
        self.assertIn("nothing to change", r.stdout, r.stdout[-3000:])
        print("[e2e] whole flow in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    unittest.main()
