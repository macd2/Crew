"""The owner's template overrides: <default home>/crew/templates/<role>/ sits outside the package, so an update
never touches it. Its settings.conf replaces the shipped keys one by one (a key the template lacks is added),
and its SOUL.md replaces the shipped persona. With no override the shipped template applies unchanged."""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import module_env  # noqa: E402  - import-time env pins, undone when the module ends (issue #15)
module_env.pin(globals(), HERMES_BIN="/bin/false")
from hermes_fake import FakeConfig  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("crew_install_overrides", str(REPO / "install.py"))
CI = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CI)

SHIPPED = ("# shipped\ncrew.role = worker\nmodel.default = shipped-model\nagent.max_turns = 150\n"
           "skills_extra = [a/b, c/d]\n")


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


class OverrideTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp(prefix="crew-overrides-unit-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.tpl = os.path.join(tmp, "package", "templates", "profiles", "worker")
        self.over = os.path.join(tmp, "overrides")
        self.conf = os.path.join(self.tpl, "settings.conf")
        put(self.conf, SHIPPED)
        put(os.path.join(self.tpl, "SOUL.md"), "shipped persona\n")
        env = mock.patch.dict(os.environ, {"CREW_TEMPLATE_OVERRIDES": self.over})
        env.start()
        self.addCleanup(env.stop)

    def override(self, name, text):
        put(os.path.join(self.over, "worker", name), text)

    def test_without_an_override_the_shipped_template_applies_unchanged(self):
        self.assertEqual([("crew.role", "worker"), ("model.default", "shipped-model"), ("agent.max_turns", "150")],
                         CI._conf_entries(self.conf))
        self.assertEqual(["a/b", "c/d"], CI._conf_list(self.conf, "skills_extra"))
        self.assertEqual(os.path.join(self.tpl, "SOUL.md"), CI._soul_source(self.tpl))

    def test_an_override_key_replaces_the_shipped_value_in_place_and_a_new_key_is_added(self):
        self.override("settings.conf", "model.default = my-model\nmodel.provider = my-provider\n")
        self.assertEqual([("crew.role", "worker"), ("model.default", "my-model"), ("agent.max_turns", "150"),
                          ("model.provider", "my-provider")],
                         CI._conf_entries(self.conf))

    def test_an_override_list_replaces_the_shipped_list(self):
        self.override("settings.conf", "skills_extra = [e/f]\n")
        self.assertEqual(["e/f"], CI._conf_list(self.conf, "skills_extra"))

    def test_another_roles_override_does_not_apply(self):
        put(os.path.join(self.over, "verifier", "settings.conf"), "model.default = verifier-model\n")
        self.assertIn(("model.default", "shipped-model"), CI._conf_entries(self.conf))

    def test_install_and_check_agree_on_the_overridden_value(self):
        self.override("settings.conf", "model.default = my-model\n")
        cfg, saved = FakeConfig(), CI.h
        CI.h = cfg
        self.addCleanup(setattr, CI, "h", saved)
        cfg.seed("p", model__default="shipped-model")
        self.assertIn("model.default", CI._apply_settings("p", self.conf)[0])
        self.assertEqual("my-model", CI._cfg("p", "model.default"))
        self.assertEqual([], CI._apply_settings("p", self.conf)[0], "applying twice must change nothing")
        self.assertEqual([], CI.settings_problems("p", "worker", self.tpl))

    def check_with(self, **seed):
        cfg, saved = FakeConfig(), CI.h
        CI.h = cfg
        self.addCleanup(setattr, CI, "h", saved)
        cfg.seed("p", **seed)
        return cfg

    def test_a_gate_key_is_skipped_and_check_reports_it(self):
        self.override("settings.conf", "platforms.slack.enabled = true\nmodel.default = my-model\n")
        self.assertNotIn(("platforms.slack.enabled", "true"), CI._conf_entries(self.conf))
        self.assertIn(("model.default", "my-model"), CI._conf_entries(self.conf))
        self.check_with(crew__role="worker", model__default="my-model", agent__max_turns="150")
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("platforms.slack.enabled is not an owner key", problems[0])

    def test_crew_role_cannot_be_overridden(self):
        self.override("settings.conf", "crew.role = coordinator\n")
        self.assertIn(("crew.role", "worker"), CI._conf_entries(self.conf))
        self.check_with(crew__role="worker", model__default="shipped-model", agent__max_turns="150")
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("crew.role is not an owner key", problems[0])

    def test_a_key_written_twice_is_refused_and_reported(self):
        self.override("settings.conf", "model.default = one\nmodel.default = two\nagent.max_turns = 90\n")
        self.assertIn(("model.default", "shipped-model"), CI._conf_entries(self.conf))
        self.assertIn(("agent.max_turns", "90"), CI._conf_entries(self.conf))
        self.check_with(crew__role="worker", model__default="shipped-model", agent__max_turns="90")
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("model.default is written 2 times", problems[0])

    def test_fallback_providers_is_an_owner_key(self):
        self.override("settings.conf", "fallback_providers = [{provider: p, model: m}]\n")
        self.assertIn(("fallback_providers", "[{provider: p, model: m}]"), CI._conf_entries(self.conf))
        self.assertEqual([], CI._override_lines(self.conf)[1])

    def test_a_fallback_list_of_mappings_converges(self):
        # Hermes prints a list of mappings as a YAML block; the override writes it as JSON. Same value: once applied,
        # a second install changes nothing and --check is clean.
        self.override("settings.conf", 'fallback_providers = [{"provider":"litellm","model":"reason"}]\n')
        self.check_with(crew__role="worker", model__default="shipped-model", agent__max_turns="150",
                        fallback_providers="[]")
        self.assertIn("fallback_providers", CI._apply_settings("p", self.conf)[0])
        self.assertEqual([], CI._apply_settings("p", self.conf)[0], "applying twice must change nothing")
        self.assertEqual([], CI.settings_problems("p", "worker", self.tpl))

    def test_a_different_fallback_mapping_is_still_reported(self):
        self.override("settings.conf", 'fallback_providers = [{"provider":"litellm","model":"reason"}]\n')
        self.check_with(crew__role="worker", model__default="shipped-model", agent__max_turns="150",
                        fallback_providers='[{"provider":"litellm","model":"other"}]')
        problems = CI.settings_problems("p", "worker", self.tpl)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("fallback_providers", problems[0])

    def test_a_soul_override_replaces_the_shipped_persona(self):
        self.override("SOUL.md", "my persona\n")
        self.assertEqual(os.path.join(self.over, "worker", "SOUL.md"), CI._soul_source(self.tpl))

    def test_the_default_root_is_crew_templates_under_the_default_home(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CREW_TEMPLATE_OVERRIDES", None)
            self.assertEqual(os.path.join(CI.crew_card.default_home(), "crew", "templates"), CI._overrides_root())


if __name__ == "__main__":
    unittest.main()
