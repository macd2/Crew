#!/usr/bin/env python3
"""Tests for crew lineups (scripts/crew_lineup.py): validation, text resolution, path refusals, build, fetch, state."""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("HERMES_BIN", "/bin/false")

import module_env  # noqa: E402

module_env.pin(globals(), HERMES_HOME=tempfile.mkdtemp(prefix="crew-lineup-mod-"))

import crew_lineup  # noqa: E402
from crew_lineup import LineupError  # noqa: E402


def role(name="auditor", **kw):
    r = {"name": name, "purpose": "Finds problems, never fixes them."}
    r.update(kw)
    return r


class LineupCase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.home = tempfile.mkdtemp(prefix="crew-lineup-test-")
        os.environ["HERMES_HOME"] = self.home
        self.crew = os.path.join(self.home, "crew")
        os.makedirs(os.path.join(self.crew, "lineups"))

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.home, ignore_errors=True)

    def put(self, rel, text):
        p = os.path.join(self.crew, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def lineup(self, roles, name="mine", **top):
        data = dict({"name": name, "roles": roles}, **top)
        self.put("lineups/%s.json" % name, json.dumps(data))
        return name

    def errors(self, roles, **top):
        with self.assertRaises(LineupError) as cm:
            crew_lineup.load(self.lineup(roles, **top))
        return str(cm.exception)


class Validation(LineupCase):
    def test_crew_dir_is_base_home_crew(self):
        self.assertEqual(crew_lineup.crew_dir(), self.crew)
        os.environ["HERMES_HOME"] = os.path.join(self.home, "profiles", "crew-worker")
        self.assertEqual(crew_lineup.crew_dir(), self.crew)

    def test_minimal_lineup_defaults(self):
        lu = crew_lineup.load(self.lineup([role()]))
        self.assertEqual(lu["name"], "mine")
        r = lu["roles"][0]
        self.assertEqual(r["task_class"], "code")
        self.assertEqual(r["tools"], ["terminal", "file", "web", "kanban", "crew"])
        self.assertEqual(r["description"], "Crew auditor: Finds problems, never fixes them.")
        self.assertEqual(r["budget_tokens"], json.load(open(REPO / "roles" / "roles.json"))["default_budget_tokens"])
        self.assertTrue(r["artifact"] and r["proof"])
        for t in ("soul_text", "brief_text", "skill_text"):
            self.assertIn("auditor", r[t].lower())
        self.assertIn("Finds problems", r["soul_text"])
        self.assertNotIn("{", r["soul_text"] + r["brief_text"] + r["skill_text"])

    def test_name_defaults_to_stem(self):
        self.put("lineups/stemmy.json", json.dumps({"roles": [role()]}))
        self.assertEqual(crew_lineup.load("stemmy")["name"], "stemmy")

    def test_missing_purpose(self):
        self.assertIn("purpose is required", self.errors([{"name": "auditor"}]))

    def test_bad_role_name(self):
        for bad in ("Auditor", "a", "aud1tor", "aud-itor", "x" * 25):
            self.assertIn("name must be", self.errors([role(bad)]), bad)

    def test_reserved_role_names(self):
        for bad in ("coordinator", "verifier", "all"):
            self.assertIn("reserved", self.errors([role(bad)]))

    def test_duplicate(self):
        self.assertIn("duplicate", self.errors([role(), role()]))

    def test_unknown_key(self):
        msg = self.errors([role(colour="red")])
        self.assertIn("role 'auditor'", msg)
        self.assertIn("'colour'", msg)
        self.assertIn("unknown key 'extra'", self.errors([role()], extra=1))

    def test_kanban_and_crew_cannot_be_removed(self):
        self.assertIn("'kanban'", self.errors([role(no_toolsets=["kanban"])]))
        self.assertIn("'crew'", self.errors([role(no_toolsets=["crew"])]))

    def test_bad_toolset_and_lineup_name_and_count(self):
        self.assertIn("toolsets", self.errors([role(toolsets=["Bad Name"])]))
        self.assertIn("lineup name", self._bad_lineup_name())
        self.assertIn("roles must be", self.errors([]))
        self.assertIn("too many roles", self.errors([role("r" + chr(97 + i) * 2) for i in range(13)]))

    def _bad_lineup_name(self):
        self.put("lineups/x.json", json.dumps({"name": "Bad_Name", "roles": [role()]}))
        with self.assertRaises(LineupError) as cm:
            crew_lineup.load("x")
        return str(cm.exception)

    def test_every_problem_listed(self):
        msg = self.errors([{"name": "verifier"}, role(colour=1), role()])
        for part in ("reserved", "purpose is required", "unknown key 'colour'", "duplicate"):
            self.assertIn(part, msg)

    def test_default_is_reserved(self):
        with self.assertRaises(LineupError):
            crew_lineup.find("default")

    def test_toolsets_added_and_removed(self):
        r = crew_lineup.load(self.lineup([role(toolsets=["browser"], no_toolsets=["web"])]))["roles"][0]
        self.assertEqual(r["tools"], ["terminal", "file", "kanban", "crew", "browser"])


class Texts(LineupCase):
    def one(self, **kw):
        return crew_lineup.load(self.lineup([role(**kw)]))["roles"][0]

    def test_neither_string_file_both(self):
        for t in ("soul", "brief", "skill"):
            self.put("p/%s.md" % t, "FROM FILE %s\n" % t)
            self.assertEqual(self.one(**{t: "inline %s" % t})[t + "_text"], "inline %s" % t)
            self.assertEqual(self.one(**{t + "_file": "p/%s.md" % t})[t + "_text"], "FROM FILE %s" % t)
            both = self.one(**{t: "inline %s" % t, t + "_file": "p/%s.md" % t})[t + "_text"]
            self.assertEqual(both, "FROM FILE %s\n\ninline %s" % (t, t))
            self.assertIn("auditor", self.one()[t + "_text"].lower())

    def refused(self, path, want):
        with self.assertRaises(LineupError) as cm:
            self.one(soul_file=path)
        msg = str(cm.exception)
        self.assertIn("role 'auditor'", msg)
        self.assertIn("soul_file", msg)
        self.assertIn(want, msg)

    def test_path_refusals(self):
        outside = os.path.join(self.home, "secret.md")
        with open(outside, "w") as fh:
            fh.write("secret")
        self.refused(outside, "absolute")
        self.refused("~/x.md", "'~'")
        self.refused("../secret.md", "leaves the crew folder")
        self.refused("p/../../secret.md", "leaves the crew folder")
        self.refused("C:/x.md", "absolute")
        self.refused("nope/missing.md", "not found")
        os.symlink(outside, os.path.join(self.crew, "link.md"))
        self.refused("link.md", "leaves the crew folder")
        self.put("big.md", "x" * (64 * 1024 + 1))
        self.refused("big.md", "larger than")
        with open(os.path.join(self.crew, "bin.md"), "wb") as fh:
            fh.write(b"\xff\xfe\x00bad")
        self.refused("bin.md", "UTF-8")

    def test_symlink_inside_is_fine(self):
        self.put("real/s.md", "inside")
        os.symlink(os.path.join(self.crew, "real", "s.md"), os.path.join(self.crew, "alias.md"))
        self.assertEqual(self.one(soul_file="alias.md")["soul_text"], "inside")


class Build(LineupCase):
    def test_build_structure(self):
        self.put("p/skill.md", "Check every input.")
        name = self.lineup([role(model="claude-sonnet-5-5", provider="openrouter", toolsets=["browser", "memory"],
                                 no_toolsets=["web"], max_turns=40, skills_extra=["devops/thing"],
                                 skill_file="p/skill.md", budget_tokens=900000),
                            role("fixer", purpose="Fixes what the auditor found.", task_class="code")],
                           description="Test crew")
        out = crew_lineup.build(name)
        self.assertEqual(out, os.path.join(self.crew, "lineup-build", "mine"))
        for rel in ("roles/roles.json", "roles/briefs/coordinator.md", "roles/briefs/verifier.md",
                    "roles/briefs/auditor.md", "roles/briefs/fixer.md",
                    "templates/profiles/coordinator/SOUL.md", "templates/profiles/verifier/settings.conf",
                    "templates/profiles/auditor/SOUL.md", "templates/profiles/auditor/settings.conf",
                    "templates/profiles/fixer/settings.conf",
                    "skills/crew-role-auditor/SKILL.md", "skills/crew-role-fixer/SKILL.md"):
            self.assertTrue(os.path.isfile(os.path.join(out, rel)), rel)
        rj = json.load(open(os.path.join(out, "roles", "roles.json")))
        shipped = json.load(open(REPO / "roles" / "roles.json"))
        for k in shipped:
            self.assertIn(k, rj)
        self.assertEqual([(r["name"], r["kind"]) for r in rj["roles"]],
                         [("coordinator", "coordinator"), ("auditor", "writer"), ("fixer", "writer"),
                          ("verifier", "verifier")])
        aud = rj["roles"][1]
        self.assertEqual(aud["brief"], "briefs/auditor.md")
        self.assertEqual(aud["budget_tokens"], 900000)
        self.assertEqual(aud["model_class"], "cheap")
        self.assertEqual(aud["tools_allowed"], ["terminal", "file", "kanban", "crew", "browser", "memory"])
        conf = open(os.path.join(out, "templates", "profiles", "auditor", "settings.conf")).read()
        self.assertIn("crew.role = auditor\n", conf)
        self.assertIn("model.default = claude-sonnet-5-5\n", conf)
        self.assertIn("model.provider = openrouter\n", conf)
        self.assertIn("platform_toolsets.cli = [terminal,file,kanban,crew,browser,memory]\n", conf)
        self.assertIn("agent.max_turns = 40\n", conf)
        self.assertIn("skills_extra = [devops/thing]\n", conf)
        self.assertIn("agent.disabled_toolsets = [cronjob,computer_use,todo,tts]\n", conf)
        self.assertIn("{prefix}coordinator", conf)
        fixer = open(os.path.join(out, "templates", "profiles", "fixer", "settings.conf")).read()
        self.assertIn("crew.role = fixer\n", fixer)
        self.assertIn("model.default = claude-opus-5-5\n", fixer)  # template default kept
        skill = open(os.path.join(out, "skills", "crew-role-auditor", "SKILL.md")).read()
        self.assertTrue(skill.startswith("---\nname: crew-role-auditor\n"))
        self.assertIn("# Crew auditor pass", skill)
        self.assertIn("Check every input.", skill)
        for rule in (".crew/", "kanban_request_review", "crew_verdict", "kanban_complete"):
            self.assertIn(rule, skill)
        self.assertLess(skill.index("Check every input."), skill.index("## Do"))
        # rebuild is idempotent and leaves no temp dirs behind
        self.assertEqual(crew_lineup.build(name), out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.crew, "lineup-build"))), ["mine"])

    def test_build_invalid_writes_nothing(self):
        name = self.lineup([{"name": "auditor"}])
        with self.assertRaises(LineupError):
            crew_lineup.build(name)
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineup-build", "mine")))

    def test_package_lineups_listed_and_user_wins(self):
        names = {e["name"]: e for e in crew_lineup.list_lineups()}
        if (REPO / "crew-home" / "lineups" / "security.json").is_file():
            self.assertEqual(names["security"]["source"], "package")
            self.put("lineups/security.json", json.dumps({"name": "security", "roles": [role()]}))
            names = {e["name"]: e for e in crew_lineup.list_lineups()}
            self.assertEqual(names["security"]["source"], "user")
            self.assertEqual(names["security"]["roles"], ["auditor"])

    def test_preview_has_texts(self):
        text = crew_lineup.preview(self.lineup([role(soul="Be careful.")]))
        self.assertIn("auditor", text)
        self.assertIn("Be careful.", text)
        self.assertIn("--- brief (generated)", text)

    def test_cli_validate_exits_1_with_every_problem(self):
        self.lineup([{"name": "verifier"}, role(colour=1)], name="broken")
        p = subprocess.run([sys.executable, str(REPO / "scripts" / "crew_lineup.py"), "validate", "broken"],
                           capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual(p.returncode, 1)
        self.assertIn("reserved", p.stderr)
        self.assertIn("colour", p.stderr)
        self.lineup([role()], name="good")
        p = subprocess.run([sys.executable, str(REPO / "scripts" / "crew_lineup.py"), "validate", "good"],
                           capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual(p.returncode, 0, p.stderr)


class ShippedLineups(LineupCase):
    """Every lineup the package ships (crew-home/lineups/) is valid, builds, and is found by name."""

    def shipped(self):
        return sorted((REPO / "crew-home" / "lineups").glob("*.json"))

    def test_every_shipped_lineup_validates_and_builds(self):
        files = self.shipped()
        self.assertTrue({"security", "design", "pentest"} <= {f.stem for f in files}, files)
        for f in files:
            with self.subTest(lineup=f.stem):
                lu = crew_lineup.load(f.stem)
                self.assertEqual(lu["name"], f.stem)
                self.assertEqual(crew_lineup.find(f.stem), str(f))
                out = crew_lineup.build(f.stem, out_root=os.path.join(self.home, "out"))
                for r in lu["roles"]:
                    for key in ("soul", "brief", "skill"):
                        self.assertTrue(str(r.get(key) or "").strip(), "%s/%s ships its own %s" % (f.stem, r["name"], key))
                    skill = Path(out, "skills", "crew-role-%s" % r["name"], "SKILL.md").read_text(encoding="utf-8")
                    self.assertIn(r["skill"].splitlines()[0], skill)
                    self.assertIn(".crew/", skill)    # crew's writer rules are always there

    def test_shipped_lineups_are_listed_by_name(self):
        names = {e["name"]: e for e in crew_lineup.list_lineups()}
        for name in ("security", "design", "pentest"):
            self.assertEqual(names[name]["source"], "package")
        self.assertEqual(names["design"]["roles"], ["researcher", "designer", "prototyper"])
        self.assertEqual(names["pentest"]["roles"], ["recon", "tester", "reporter"])

    def test_every_pentest_role_requires_authorization_and_scope(self):
        for r in crew_lineup.load("pentest")["roles"]:
            for key in ("soul", "skill"):
                text = r[key].lower()
                self.assertIn("authoriz", text, "%s %s" % (r["name"], key))
                self.assertIn("scope", text, "%s %s" % (r["name"], key))
            self.assertIn("kanban_block", r["skill"], r["name"])


class Uninstall(LineupCase):
    def test_plan_names_the_roles_and_the_build_and_never_the_file(self):
        self.put("prompts/a.md", "text")
        name = self.lineup([role(soul_file="prompts/a.md"), role("fixer", purpose="Fixes.")])
        out = crew_lineup.build(name)
        plan = crew_lineup.uninstall_plan(name)
        self.assertEqual(["auditor", "fixer"], plan["roles"])
        self.assertEqual([out], plan["dirs"])
        crew_lineup.remove_build(plan)
        self.assertFalse(os.path.exists(out))
        self.assertTrue(os.path.isfile(os.path.join(self.crew, "lineups", "mine.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.crew, "prompts", "a.md")))
        self.assertIn("crew-auditor, crew-fixer", crew_lineup.describe_uninstall(plan))

    def test_default_and_unknown_refused(self):
        for name in ("default", "nosuch"):
            with self.assertRaises(LineupError):
                crew_lineup.uninstall_plan(name)

    def test_a_shipped_lineup_has_a_plan(self):
        plan = crew_lineup.uninstall_plan("pentest")
        self.assertEqual(["recon", "tester", "reporter"], plan["roles"])


class PluginCopy(LineupCase):
    """Loaded from a profile's plugin copy ($HERMES_HOME/plugins/crew/scripts), which has no roles/, templates/ or
    lineups/: the package comes from config crew.source_dir."""

    def test_plugin_copy_uses_source_dir(self):
        plug = os.path.join(self.home, "plugins", "crew", "scripts")
        os.makedirs(plug)
        for f in os.listdir(REPO / "scripts"):
            if f.endswith(".py"):
                shutil.copy2(str(REPO / "scripts" / f), plug)
        self.lineup([role()])
        cli = [sys.executable, os.path.join(plug, "crew_lineup.py")]
        env = dict(os.environ, CREW_PKG=os.path.join(self.home, "nowhere"))
        p = subprocess.run(cli + ["build", "mine"], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("crew.source_dir", p.stderr)
        with open(os.path.join(self.home, "config.yaml"), "w") as fh:
            fh.write("crew:\n  role: coordinator\n  source_dir: %s\n" % REPO)
        p = subprocess.run(cli + ["build", "mine"], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout.strip()
        self.assertTrue(os.path.isfile(os.path.join(out, "templates", "profiles", "auditor", "SOUL.md")))
        self.assertTrue(os.path.isfile(os.path.join(out, "roles", "briefs", "verifier.md")))
        p = subprocess.run(cli + ["list"], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("mine", p.stdout)
        if (REPO / "crew-home" / "lineups" / "security.json").is_file():
            self.assertIn("security", p.stdout)


class State(LineupCase):
    def test_state_roundtrip(self):
        self.assertEqual(crew_lineup.read_state(), {})
        crew_lineup.write_state(active="mine", status="building", roles=["auditor"], source="/x.json", error="")
        st = crew_lineup.write_state(status="ready")
        self.assertEqual(st["active"], "mine")
        self.assertEqual(st["status"], "ready")
        self.assertIsInstance(st["updated"], int)
        self.assertEqual(crew_lineup.read_state(), st)
        self.assertTrue(os.path.isfile(os.path.join(self.crew, "lineup.json")))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class Fetch(LineupCase):
    def serve(self, root):
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=root))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return "http://127.0.0.1:%d/" % httpd.server_address[1]

    def test_fetch_url_and_commit(self):
        site = tempfile.mkdtemp(dir=self.home)
        os.makedirs(os.path.join(site, "lineups", "prompts", "auditor"))
        with open(os.path.join(site, "lineups", "prompts", "auditor", "SOUL.md"), "w") as fh:
            fh.write("Remote soul.")
        with open(os.path.join(site, "lineups", "remote.json"), "w") as fh:
            json.dump({"roles": [role(soul_file="prompts/auditor/SOUL.md")]}, fh)
        for k in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
            os.environ.pop(k, None)
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        url = self.serve(site) + "lineups/remote.json"
        name, text = crew_lineup.fetch(url)
        self.assertEqual(name, "remote")
        self.assertIn("Remote soul.", text)
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineups", "remote.json")))
        self.put("prompts/auditor/SOUL.md", "old")
        res = crew_lineup.commit_pending("remote")
        self.assertEqual(res["path"], os.path.join(self.crew, "lineups", "remote.json"))
        self.assertEqual(res["overwritten"], [os.path.join(self.crew, "prompts", "auditor", "SOUL.md")])
        self.assertEqual(open(os.path.join(self.crew, "prompts", "auditor", "SOUL.md")).read(), "Remote soul.")
        self.assertEqual(crew_lineup.load("remote")["roles"][0]["soul_text"], "Remote soul.")
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineups", ".pending", "remote")))
        with self.assertRaises(LineupError):
            crew_lineup.commit_pending("remote")

    def test_fetch_local_with_dest_name(self):
        src = tempfile.mkdtemp(dir=self.home)
        with open(os.path.join(src, "b.md"), "w") as fh:
            fh.write("Local brief.")
        path = os.path.join(src, "x.json")
        with open(path, "w") as fh:
            json.dump({"name": "x", "roles": [role(brief_file="b.md")]}, fh)
        name, text = crew_lineup.fetch(path, dest_name="renamed")
        self.assertEqual(name, "renamed")
        self.assertIn("Local brief.", text)
        crew_lineup.commit_pending("renamed")
        self.assertEqual(crew_lineup.load("renamed")["name"], "renamed")

    def test_fetch_refuses_escaping_paths_and_invalid(self):
        src = tempfile.mkdtemp(dir=self.home)
        path = os.path.join(src, "bad.json")
        with open(path, "w") as fh:
            json.dump({"roles": [role(soul_file="../../etc/passwd")]}, fh)
        with self.assertRaises(LineupError):
            crew_lineup.fetch(path)
        with open(path, "w") as fh:
            json.dump({"roles": [{"name": "auditor"}]}, fh)
        with self.assertRaises(LineupError):
            crew_lineup.fetch(path)
        self.assertFalse(os.path.exists(os.path.join(self.crew, "lineups", ".pending", "bad")))


if __name__ == "__main__":
    unittest.main()
