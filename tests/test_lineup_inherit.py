"""Lineup `inherit` blocks and the installer's inherit.* lines: validation, defaults, override order, and what a role
profile really gets (.env, credential sections, hooks, MCP servers, skills) through the fake hermes in a scratch HOME."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_install_lineup as TIL  # noqa: E402  (imports the module, so its own test classes are not re-collected)
import test_crew_lineup as TCL  # noqa: E402
from hermes_fake import Proc  # noqa: E402

CI = TIL.CI
crew_lineup = TCL.crew_lineup
LineupError = TCL.LineupError
DEFAULTS = {"env": "owner", "hooks": "owner", "skills": False, "mcp": False}
HOOKS = {"pre_tool_call": [{"command": "/bin/true"}]}
SERVERS = {"github": {"command": "gh-mcp"}, "slack": {"command": "slack-mcp"}}
SECRETS = {"provider": "vault", "path": "kv/x"}
ROLES = ("coordinator", "worker", "content", "verifier")


def _creds(path):
    return [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def _skill(home, category, name):
    d = Path(home, "skills", category, name) if category else Path(home, "skills", name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: %s\n---\n" % name, encoding="utf-8")


class _LineupHome(TCL.LineupCase):
    """The owner is the default profile (self.home); `other` is a second profile. Both have skills and MCP servers:
    owner skills seo-search, github, shared; owner servers github, slack; other skills deploy, shared; servers jira."""
    def setUp(self):
        super().setUp()
        self.other = os.path.join(self.home, "profiles", "other")
        os.makedirs(self.other)
        for cat, name in (("marketing", "seo-search"), ("devops", "github"), ("zz", "shared")):
            _skill(self.home, cat, name)
        _skill(self.home, "crew", "crew-role-x")            # crew's own: never part of a set
        for cat, name in (("ops", "deploy"), ("aa", "shared")):
            _skill(self.other, cat, name)
        self.servers(self.home, SERVERS)
        self.servers(self.other, {"jira": {"command": "jira-mcp"}})

    def servers(self, home, mapping):
        import yaml
        Path(home, "config.yaml").write_text(yaml.safe_dump({"mcp_servers": mapping}), encoding="utf-8")

    def make_profile(self, name):
        os.makedirs(os.path.join(self.home, "profiles", name), exist_ok=True)

    def resolved(self, key, spec):
        got, errs = crew_lineup.resolve_set(key, spec, crew_lineup._default_sources())
        self.assertEqual([], errs)
        return got

    def inherit_of(self, roles, **top):
        return [r["inherit"] for r in crew_lineup.load(self.lineup(roles, **top))["roles"]]


class InheritValidation(_LineupHome):
    def test_unknown_key_at_top_level_names_the_field(self):
        msg = self.errors([TCL.role()], inherit={"colour": "owner"})
        self.assertIn("top level: inherit has unknown key 'colour'", msg)

    def test_unknown_key_in_a_role_names_the_role(self):
        msg = self.errors([TCL.role(inherit={"nope": False})])
        self.assertIn("inherit has unknown key 'nope'", msg)
        self.assertIn("auditor", msg)

    def test_inherit_that_is_not_an_object_is_refused(self):
        self.assertIn("inherit must be an object", self.errors([TCL.role()], inherit=["env"]))

    def test_wrong_types_are_refused_and_the_text_names_the_field(self):
        for key, val in (("env", 5), ("env", True), ("env", {"from": "owner"}), ("env", ["a"]), ("hooks", ["a"]),
                         ("hooks", 1.5), ("mcp", True), ("skills", 3), ("env", None), ("mcp", None)):
            with self.subTest(key=key, val=val):
                self.assertIn("inherit.%s must be" % key, self.errors([TCL.role(inherit={key: val})]))

    def test_object_form_type_errors(self):
        for val, text in (({"from": 5}, "inherit.skills.from must be"),
                          ({"add": ["seo-search"]}, "inherit.skills needs \"from\""),
                          ({"from": False, "add": "seo-search"}, "inherit.skills.add must be a list"),
                          ({"from": False, "add": [3]}, "inherit.skills.add must list skill names"),
                          ({"from": "owner", "drop": ["other/github"]}, "inherit.skills.drop must list skill names"),
                          ({"from": "owner", "drop": "github"}, "inherit.skills.drop must list"),
                          ({"from": "owner", "keep": []}, "inherit.skills has unknown key 'keep'")):
            with self.subTest(val=val):
                self.assertIn(text, self.errors([TCL.role(inherit={"skills": val})]))

    def test_list_with_a_bad_name_is_refused(self):
        self.assertIn("inherit.mcp must list MCP server names", self.errors([TCL.role(inherit={"mcp": ["ok", "bad name!"]})]))
        self.assertIn("inherit.skills must list skill names", self.errors([TCL.role(inherit={"skills": ["../x"]})]))
        self.assertIn("inherit.skills must list", self.errors([TCL.role(inherit={"skills": ["a/b/c"]})]))
        self.assertIn("inherit.mcp must list", self.errors([TCL.role(inherit={"mcp": ["a", 3]})]))

    def test_non_existent_profile_is_refused_in_every_place_a_profile_is_named(self):
        self.assertIn("inherit.env: no Hermes profile 'ghost'", self.errors([TCL.role(inherit={"env": "ghost"})]))
        self.assertIn("inherit.hooks: no Hermes profile 'ghost'", self.errors([TCL.role()], inherit={"hooks": "ghost"}))
        self.assertIn("inherit.skills: no Hermes profile 'ghost'", self.errors([TCL.role(inherit={"skills": "ghost"})]))
        self.assertIn("inherit.mcp: no Hermes profile 'ghost'",
                      self.errors([TCL.role(inherit={"mcp": ["github", "ghost/github"]})]))
        self.assertIn("inherit.skills: no Hermes profile 'ghost'",
                      self.errors([TCL.role(inherit={"skills": {"from": "ghost"}})]))
        self.assertIn("inherit.skills: no Hermes profile 'ghost'",
                      self.errors([TCL.role(inherit={"skills": {"from": False, "add": ["ghost/x"]}})]))

    def test_string_false_is_refused(self):
        self.assertIn("inherit.env 'false': must be a profile name", self.errors([TCL.role(inherit={"env": "false"})]))

    def test_a_named_skill_or_server_missing_in_its_source_profile_is_refused(self):
        self.assertIn("inherit.skills: the owner profile has no skill 'ghost-skill'",
                      self.errors([TCL.role(inherit={"skills": ["ghost-skill"]})]))
        self.assertIn("inherit.skills: profile 'other' has no skill 'seo-search'",
                      self.errors([TCL.role(inherit={"skills": ["other/seo-search"]})]))
        self.assertIn("inherit.mcp: the owner profile has no MCP server 'jira'",
                      self.errors([TCL.role(inherit={"mcp": {"from": False, "add": ["jira"]}})]))
        self.assertIn("inherit.mcp: profile 'other' has no MCP server 'nosuch'",
                      self.errors([TCL.role()], inherit={"mcp": ["other/nosuch"]}))

    def test_drop_of_a_name_not_in_the_set_is_refused(self):
        msg = self.errors([TCL.role(inherit={"mcp": {"from": "other", "drop": ["github"]}})])
        self.assertIn("inherit.mcp: drop 'github' is not in the set (jira)", msg)
        self.assertIn("drop 'x' is not in the set (empty)",
                      self.errors([TCL.role(inherit={"skills": {"from": False, "drop": ["x"]}})]))

    def test_a_top_level_problem_is_reported_once_for_every_role(self):
        msg = self.errors([TCL.role("alpha"), TCL.role("bravo")], inherit={"skills": ["ghost-skill"]})
        self.assertEqual(1, msg.count("ghost-skill"), msg)
        self.assertIn("top level: inherit.skills", msg)

    def test_crew_skills_are_not_a_set_member(self):
        self.assertIn("no skill 'crew-role-x'", self.errors([TCL.role(inherit={"skills": ["crew-role-x"]})]))

    def test_empty_list_means_false(self):
        self.assertEqual([False], [i["mcp"] for i in self.inherit_of([TCL.role(inherit={"mcp": []})])])


class InheritForms(_LineupHome):
    """The four forms, as normalized by load and as resolved (the exact set a role gets)."""
    def test_1_a_profile_name_is_everything_that_profile_has(self):
        inh = self.inherit_of([TCL.role(inherit={"skills": "other", "mcp": "owner"})])[0]
        self.assertEqual(("other", "owner"), (inh["skills"], inh["mcp"]))
        self.assertEqual({"deploy": ("other", "ops/deploy"), "shared": ("other", "aa/shared")},
                         self.resolved("skills", "other"))
        self.assertEqual({"github": ("owner", SERVERS["github"]), "slack": ("owner", SERVERS["slack"])},
                         self.resolved("mcp", "owner"))

    def test_2_a_list_is_exactly_that_list_bare_from_owner_slash_from_that_profile(self):
        inh = self.inherit_of([TCL.role(inherit={"skills": ["seo-search", "other/deploy"],
                                                 "mcp": ["slack", "other/jira"]})])[0]
        self.assertEqual(["seo-search", "other/deploy"], inh["skills"])
        self.assertEqual({"seo-search": ("owner", "marketing/seo-search"), "deploy": ("other", "ops/deploy")},
                         self.resolved("skills", inh["skills"]))
        self.assertEqual({"slack": ("owner", SERVERS["slack"]), "jira": ("other", {"command": "jira-mcp"})},
                         self.resolved("mcp", inh["mcp"]))

    def test_3_an_object_is_from_plus_add_minus_drop(self):
        spec = {"from": "other", "add": ["owner/seo-search", "github"], "drop": ["deploy"]}
        inh = self.inherit_of([TCL.role(inherit={"skills": spec})])[0]
        self.assertEqual(spec, inh["skills"])
        self.assertEqual({"shared": ("other", "aa/shared"), "seo-search": ("owner", "marketing/seo-search"),
                          "github": ("owner", "devops/github")}, self.resolved("skills", spec))
        self.assertEqual({"jira": ("other", {"command": "jira-mcp"}), "github": ("owner", SERVERS["github"])},
                         self.resolved("mcp", {"from": "owner", "add": ["other/jira"], "drop": ["slack"]}))

    def test_3_from_false_starts_empty_and_add_and_drop_default_to_nothing(self):
        self.assertEqual({"jira": ("other", {"command": "jira-mcp"})},
                         self.resolved("mcp", {"from": False, "add": ["other/jira"]}))
        inh = self.inherit_of([TCL.role(inherit={"mcp": {"from": "owner"}})])[0]
        self.assertEqual({"from": "owner", "add": [], "drop": []}, inh["mcp"])
        self.assertEqual(["github", "slack"], sorted(self.resolved("mcp", inh["mcp"])))

    def test_4_false_is_none(self):
        self.assertEqual({}, self.resolved("skills", False))
        self.assertEqual({}, self.resolved("mcp", False))

    def test_merge_order_an_add_replaces_the_inherited_name_and_duplicates_resolve_to_one(self):
        # `shared` is in other (aa/shared) and in the owner (zz/shared): the add of the owner's wins over the from set
        got = self.resolved("skills", {"from": "other", "add": ["owner/shared", "shared", "other/shared"]})
        self.assertEqual({"deploy": ("other", "ops/deploy"), "shared": ("owner", "zz/shared")}, got)
        # the first add of a name wins over a later one, a repeated item is one
        got = self.resolved("skills", ["other/shared", "shared", "other/shared"])
        self.assertEqual({"shared": ("other", "aa/shared")}, got)
        inh = self.inherit_of([TCL.role(inherit={"skills": ["seo-search", "seo-search"]})])[0]
        self.assertEqual(["seo-search"], inh["skills"])

    def test_drop_runs_after_add(self):
        self.assertEqual({"deploy": ("other", "ops/deploy")},
                         self.resolved("skills", {"from": "other", "add": ["seo-search"], "drop": ["seo-search", "shared"]}))

    def test_a_skill_name_two_categories_share_is_the_first_in_sorted_order(self):
        _skill(self.home, "aa", "github")
        self.assertEqual({"github": ("owner", "aa/github")}, self.resolved("skills", ["github"]))

    def test_settings_conf_round_trip_of_every_form(self):
        exists = lambda p: os.path.isdir(os.path.join(self.home, "profiles", p))  # noqa: E731
        for spec in (False, "other", ["seo-search", "other/deploy"],
                     {"from": False, "add": ["other/jira"], "drop": []},
                     {"from": "owner", "add": ["other/jira"], "drop": ["slack"]}):
            with self.subTest(spec=spec):
                lu = crew_lineup.load(self.lineup([TCL.role(inherit={"mcp": spec if spec != ["seo-search", "other/deploy"]
                                                                     else ["github", "other/jira"]})]))
                r = lu["roles"][0]
                conf = crew_lineup._settings(r)
                pairs = [tuple(x.strip() for x in l.split("=", 1)) for l in conf.splitlines() if l.startswith("inherit.")]
                back, errs = crew_lineup.conf_inherit(pairs, exists)
                self.assertEqual([], errs)
                self.assertEqual(r["inherit"], back)

    def test_conf_inherit_reports_a_bad_line(self):
        back, errs = crew_lineup.conf_inherit([("inherit.mcp", '{"from": "owner", "bogus": 1}'),
                                               ("inherit.colour", "x")], lambda p: True)
        self.assertEqual(DEFAULTS, back)
        self.assertTrue(any("unknown key 'bogus'" in e for e in errs), errs)
        self.assertTrue(any("unknown key 'colour'" in e for e in errs), errs)


class InheritDefaultsAndOrder(_LineupHome):
    def test_no_inherit_gives_every_role_the_defaults_in_dict_and_settings(self):
        lu = crew_lineup.load(self.lineup([TCL.role("alpha"), TCL.role("bravo")]))
        for r in lu["roles"]:
            self.assertEqual(DEFAULTS, r["inherit"])
            conf = crew_lineup._settings(r)
            for line in ("inherit.env = owner", "inherit.hooks = owner", "inherit.skills = false", "inherit.mcp = false"):
                self.assertIn(line, conf.splitlines())

    def test_role_overrides_top_key_by_key_and_other_roles_keep_the_top(self):
        a, b = self.inherit_of([TCL.role("alpha", inherit={"env": False}), TCL.role("bravo")],
                               inherit={"env": "other", "mcp": ["github"]})
        self.assertEqual({"env": False, "hooks": "owner", "skills": False, "mcp": ["github"]}, a)
        self.assertEqual({"env": "other", "hooks": "owner", "skills": False, "mcp": ["github"]}, b)
        lu = crew_lineup.load(self.lineup([TCL.role("alpha", inherit={"env": False})],
                                          inherit={"env": "other", "mcp": ["github"]}))
        conf = crew_lineup._settings(lu["roles"][0]).splitlines()
        self.assertIn("inherit.env = false", conf)
        self.assertIn("inherit.mcp = [github]", conf)

    def test_a_role_object_replaces_the_top_list_whole_not_merged(self):
        a, b = self.inherit_of([TCL.role("alpha", inherit={"skills": {"from": "other", "drop": ["shared"]}}),
                                TCL.role("bravo")], inherit={"skills": ["seo-search"]})
        self.assertEqual({"from": "other", "add": [], "drop": ["shared"]}, a["skills"])
        self.assertEqual({"deploy": ("other", "ops/deploy")}, self.resolved("skills", a["skills"]))
        self.assertEqual(["seo-search"], b["skills"])

    def test_a_role_false_replaces_a_top_set(self):
        a, = self.inherit_of([TCL.role(inherit={"mcp": False})], inherit={"mcp": "owner"})
        self.assertIs(False, a["mcp"])


class _Box(TIL._InstallBox):
    """The install box plus: profile create is recorded and seeds the comment-only .env Hermes seeds."""
    def setUp(self):
        super().setUp()
        self.created = []
        self.write_owner()

    def fake_h(self, profile, *args):
        if args[:2] == ("profile", "create"):
            self.created.append(args)
            r = super().fake_h(profile, *args)
            Path(self.home(args[2]), ".env").write_text("# Hermes placeholder\n", encoding="utf-8")
            return r
        return super().fake_h(profile, *args)

    def write_owner(self):
        Path(self.home("chat"), ".env").write_text("ANTHROPIC_API_KEY=x\n", encoding="utf-8")
        self.cfg.seed("chat", hooks=json.dumps(HOOKS), mcp_servers=json.dumps(SERVERS), secrets=json.dumps(SECRETS))

    def make_profile(self, name, env=None):
        os.makedirs(os.path.join(self.profiles, name, "skills"), exist_ok=True)
        if env:
            Path(self.profiles, name, ".env").write_text(env, encoding="utf-8")
        return os.path.join(self.profiles, name)

    def assertConverges(self):
        rc, out = self.run_installer("--check")
        self.assertEqual(0, rc, out)
        self.assertIn("nothing to change", out)


class InstallInheritDefaults(_Box):
    def test_shipped_crew_roles_get_env_hooks_secrets_and_no_mcp(self):
        rc, out = self.run_installer()
        self.assertEqual(0, rc, out)
        for role in ROLES:
            name = "crew-" + role
            env = os.path.join(self.home(name), ".env")
            self.assertEqual("ANTHROPIC_API_KEY=x\n", Path(env).read_text(encoding="utf-8"), name)
            if CI.POSIX_MODES:
                self.assertEqual(0o600, stat.S_IMODE(os.stat(env).st_mode), name)
            conf = self.cfg.store[name]
            self.assertEqual(HOOKS, json.loads(conf["hooks"]), name)
            self.assertEqual(SECRETS, json.loads(conf["secrets"]), name)
            self.assertEqual({}, json.loads(conf.get("mcp_servers") or "{}"), name)
            self.assertIn((name, "hooks"), self.cfg.forced)
        self.assertTrue(self.created)
        for args in self.created:
            self.assertIn("--no-skills", args)
            self.assertNotIn("--clone-from", args)

    def test_second_check_converges(self):
        self.assertEqual(0, self.run_installer()[0])
        self.assertConverges()

    def test_mcp_servers_on_a_role_are_cleared_with_force(self):
        self.assertEqual(0, self.run_installer()[0])
        self.cfg.store["crew-worker"]["mcp_servers"] = json.dumps(SERVERS)
        rc, out = self.run_installer("--check")
        self.assertEqual(1, rc, out)
        self.assertEqual(0, self.run_installer()[0])
        self.assertEqual({}, json.loads(self.cfg.store["crew-worker"]["mcp_servers"]))
        self.assertIn(("crew-worker", "mcp_servers"), self.cfg.forced)

    def test_drifted_hooks_on_a_role_are_reported_and_repaired(self):
        self.assertEqual(0, self.run_installer()[0])
        self.cfg.store["crew-worker"]["hooks"] = "{}"
        rc, out = self.run_installer("--check")
        self.assertEqual(1, rc, out)
        self.assertEqual(0, self.run_installer()[0])
        self.assertEqual(HOOKS, json.loads(self.cfg.store["crew-worker"]["hooks"]))


class InstallInheritLineup(_Box):
    def test_each_field_from_a_lineup(self):
        other = self.make_profile("other", env="OTHER_KEY=1\n")
        os.makedirs(os.path.join(other, "skills", "devops", "foo"))
        Path(other, "skills", "devops", "foo", "SKILL.md").write_text("---\nname: foo\n---\n", encoding="utf-8")
        os.makedirs(os.path.join(other, "skills", "crew", "skip"))
        Path(other, "skills", ".hidden").mkdir()
        owner_skill = os.path.join(self.home("chat"), "skills", "tools", "bar")
        os.makedirs(owner_skill)
        Path(owner_skill, "SKILL.md").write_text("---\nname: bar\n---\n", encoding="utf-8")
        self.cfg.seed("other", secrets=json.dumps({"provider": "other"}))
        self.write_lineup({"name": "duo", "description": "d", "roles": [
            {"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them.",
             "inherit": {"env": "other", "hooks": False, "skills": "other", "mcp": ["github"]}},
            {"name": "fixer", "purpose": "Fixes what the auditor found.", "inherit": {"skills": ["bar"]}}]})
        rc, out = self.run_installer("--lineup", "duo")
        self.assertEqual(0, rc, out)
        aud, fix = self.home("crew-auditor"), self.home("crew-fixer")
        self.assertEqual(["OTHER_KEY=1"], _creds(os.path.join(aud, ".env")))
        self.assertEqual({"provider": "other"}, json.loads(self.cfg.store["crew-auditor"]["secrets"]))
        self.assertEqual({}, json.loads(self.cfg.store["crew-auditor"].get("hooks") or "{}"))
        self.assertEqual({"github": SERVERS["github"]}, json.loads(self.cfg.store["crew-auditor"]["mcp_servers"]))
        self.assertIn(("crew-auditor", "mcp_servers"), self.cfg.forced)
        self.assertTrue(os.path.isfile(os.path.join(aud, "skills", "devops", "foo", "SKILL.md")))
        self.assertFalse(os.path.exists(os.path.join(aud, "skills", ".hidden")))
        self.assertFalse(os.path.exists(os.path.join(aud, "skills", "crew", "skip")))
        self.assertTrue(os.path.isfile(os.path.join(fix, "skills", "tools", "bar", "SKILL.md")))
        self.assertEqual(["ANTHROPIC_API_KEY=x"], _creds(os.path.join(fix, ".env")))
        self.assertEqual(HOOKS, json.loads(self.cfg.store["crew-fixer"]["hooks"]))
        self.assertConverges()

    def test_env_false_strips_credentials_from_an_existing_role_profile(self):
        self.write_lineup({"name": "duo", "inherit": {"env": False}, "roles": TIL.DUO["roles"]})
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        env = os.path.join(self.home("crew-auditor"), ".env")
        self.assertEqual([], _creds(env))
        Path(env).write_text("# keep\nOPENAI_API_KEY=leak\n", encoding="utf-8")
        rc, out = self.run_installer("--check")
        self.assertEqual(1, rc, out)
        rc, out = self.run_installer()
        self.assertEqual(0, rc, out)
        self.assertEqual([], _creds(env))
        self.assertEqual({}, json.loads(self.cfg.store["crew-auditor"].get("secrets") or "{}"))
        self.assertConverges()


class InstallInheritSets(_Box):
    """The list and object forms through the installer: the exact skills folders and mcp_servers a role ends up with."""
    def setUp(self):
        super().setUp()
        for cat, name in (("marketing", "seo-search"), ("devops", "github"), ("zz", "shared")):
            _skill(self.home("chat"), cat, name)
        other = self.make_profile("other")
        for cat, name in (("ops", "deploy"), ("aa", "shared")):
            _skill(other, cat, name)
        self.cfg.seed("other", mcp_servers=json.dumps({"jira": {"command": "jira-mcp"}}))

    def skills(self, profile):
        root = Path(self.home(profile), "skills")
        return sorted(p.parent.relative_to(root).as_posix() for p in root.rglob("SKILL.md")
                      if not p.parent.relative_to(root).as_posix().startswith(("crew/", "autonomous-ai-agents/")))

    def servers(self, profile):
        return json.loads(self.cfg.store[profile].get("mcp_servers") or "{}")

    def test_object_and_list_forms_give_the_exact_sets_and_converge(self):
        self.write_lineup({"name": "duo", "roles": [
            {"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them.",
             "inherit": {"skills": {"from": "owner", "add": ["other/deploy"], "drop": ["github"]},
                         "mcp": {"from": "owner", "add": ["other/jira"], "drop": ["slack"]}}},
            {"name": "fixer", "purpose": "Fixes what the auditor found.",
             "inherit": {"skills": ["github", "other/shared"], "mcp": ["other/jira"]}}]})
        rc, out = self.run_installer("--lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertEqual(["marketing/seo-search", "ops/deploy", "zz/shared"], self.skills("crew-auditor"))
        self.assertEqual({"github": SERVERS["github"], "jira": {"command": "jira-mcp"}}, self.servers("crew-auditor"))
        self.assertEqual(["aa/shared", "devops/github"], self.skills("crew-fixer"))
        self.assertEqual({"jira": {"command": "jira-mcp"}}, self.servers("crew-fixer"))
        self.assertIn(("crew-fixer", "mcp_servers"), self.cfg.forced)
        self.assertConverges()

    def test_a_skill_dropped_from_the_lineup_is_removed_from_the_role(self):
        lineup = {"name": "duo", "roles": [{"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them.",
                                            "inherit": {"skills": ["github", "seo-search"]}}]}
        self.write_lineup(lineup)
        self.assertEqual(0, self.run_installer("--lineup", "duo")[0])
        self.assertEqual(["devops/github", "marketing/seo-search"], self.skills("crew-auditor"))
        lineup["roles"][0]["inherit"]["skills"] = {"from": False, "add": ["seo-search"]}
        self.write_lineup(lineup)
        rc, out = self.run_installer("--lineup", "duo")
        self.assertEqual(0, rc, out)
        self.assertEqual(["marketing/seo-search"], self.skills("crew-auditor"))
        self.assertConverges()


class InstallInheritFailures(_Box):
    def test_mcp_server_the_owner_lacks_refuses_the_lineup_naming_it(self):
        self.write_lineup({"name": "duo", "inherit": {"mcp": ["github", "nosuch"]}, "roles": TIL.DUO["roles"]})
        rc, out = self.run_installer("--lineup", "duo")
        self.assertIn("the owner profile has no MCP server 'nosuch'", out)
        self.assertIn("refused", out)
        self.assertNotEqual(0, rc, out)
        self.assertFalse(os.path.isdir(self.home("crew-auditor")), "a refused lineup creates nothing")

    def test_inherit_skill_that_does_not_exist_refuses_the_lineup_naming_it(self):
        self.write_lineup({"name": "duo", "inherit": {"skills": ["ghost-skill"]}, "roles": TIL.DUO["roles"]})
        rc, out = self.run_installer("--lineup", "duo")
        self.assertIn("the owner profile has no skill 'ghost-skill'", out)
        self.assertNotEqual(0, rc, out)

    def test_a_template_with_a_bad_inherit_line_fails_skills_and_inherit_by_the_same_rules(self):
        """A role template's settings.conf is checked by crew_lineup's rules too: a skill the owner lacks, a server
        the owner lacks, a drop not in the set, an unknown object key."""
        self.assertEqual(0, self.run_installer()[0])
        home, src = self.home("crew-worker"), self.home("chat")
        for line, text in (('inherit.skills = {"from": false, "add": ["ghost-skill"]}', "no skill 'ghost-skill'"),
                           ("inherit.skills = [ghost-skill]", "no skill 'ghost-skill'"),
                           ('inherit.mcp = {"from": "owner", "drop": ["nosuch"]}', "drop 'nosuch' is not in the set"),
                           ("inherit.mcp = [github,nosuch]", "no MCP server 'nosuch'"),
                           ('inherit.mcp = {"from": "owner", "keep": 1}', "unknown key 'keep'")):
            with self.subTest(line=line):
                tpl = os.path.dirname(self._conf(line + "\n"))
                problems = CI.inherit_problems("crew-worker", home, tpl, "chat")
                if line.startswith("inherit.skills"):
                    status, detail = CI.step_role_skills(home, tpl, src, False)
                    self.assertEqual("FAILED", status, detail)
                    self.assertIn(text, detail)
                else:
                    self.assertTrue(any(text in p for p in problems), problems)
                    _changed, failed = CI.apply_inherit("crew-worker", home, tpl, "chat")
                    self.assertTrue(any(text in f for f in failed), failed)

    def _conf(self, text):
        d = tempfile.mkdtemp(prefix="crew-inherit-conf-")
        self.addCleanup(__import__("shutil").rmtree, d, ignore_errors=True)
        path = os.path.join(d, "settings.conf")
        Path(path).write_text(text, encoding="utf-8")
        return path

    def test_whole_section_list_is_set_with_force_so_the_guard_does_not_refuse_it(self):
        self.cfg.refuse_unforced.add("mcp_servers")
        changed, failed = CI._apply_settings("p", self._conf("mcp_servers = [a,b]\n"))
        self.assertEqual(["mcp_servers"], changed)
        self.assertEqual([], failed)
        self.assertIn(("p", "mcp_servers"), self.cfg.forced)

    def test_dotted_key_is_not_forced(self):
        changed, failed = CI._apply_settings("p", self._conf("agent.max_turns = 5\n"))
        self.assertEqual((["agent.max_turns"], []), (changed, failed))
        self.assertNotIn(("p", "agent.max_turns"), self.cfg.forced)

    def test_a_failing_set_lands_in_failed_not_changed(self):
        real = CI.h

        def failing(profile, *args):
            if args[:2] == ("config", "set") and "bad.key" in args:
                r = Proc()
                r.returncode, r.stderr = 1, "boom"
                return r
            return real(profile, *args)
        with mock.patch.object(CI, "h", failing):
            changed, failed = CI._apply_settings("p", self._conf("bad.key = 1\ngood.key = 2\n"))
        self.assertEqual(["good.key"], changed)
        self.assertEqual(1, len(failed))
        self.assertIn("bad.key", failed[0])
        self.assertIn("boom", failed[0])


if __name__ == "__main__":
    unittest.main()
