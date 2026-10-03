"""--publish puts an identity in front of the dashboard: the tailnet name gets in only with the owner's login."""
import os
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)

import crew_graph_serve as S  # noqa: E402
import install as CI  # noqa: E402


class TailnetLoginTests(unittest.TestCase):
    def test_loopback_needs_no_login(self):
        self.assertTrue(S.tailnet_user_ok("127.0.0.1:8799", "", 8799))

    def test_a_tailnet_request_needs_an_allowed_login(self):
        with mock.patch.dict(os.environ, {"CREW_GRAPH_USERS": "owner@example.com"}):
            self.assertTrue(S.tailnet_user_ok("box.ts.net:8445", "Owner@Example.com", 8799))
            self.assertFalse(S.tailnet_user_ok("box.ts.net:8445", "someone@example.com", 8799))
            self.assertFalse(S.tailnet_user_ok("box.ts.net:8445", "", 8799))  # a tagged device sends no login

    def test_no_users_configured_means_no_tailnet_access(self):
        with mock.patch.dict(os.environ, {"CREW_GRAPH_USERS": ""}):
            self.assertFalse(S.tailnet_user_ok("box.ts.net:8445", "owner@example.com", 8799))


class TaggedDeviceTests(unittest.TestCase):
    def test_a_tagged_device_gets_in_by_its_tag_and_only_by_an_allowed_one(self):
        env = {"CREW_GRAPH_USERS": "owner@example.com", "CREW_GRAPH_TAGS": "tag:admin"}
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(S, "peer_tags", side_effect=lambda ip: {"100.1.1.1": {"tag:admin"},
                                                                          "100.2.2.2": {"tag:phone"}}.get(ip, set())):
            self.assertTrue(S.tailnet_user_ok("box.ts.net:8445", "", 8799, "100.1.1.1"))
            self.assertFalse(S.tailnet_user_ok("box.ts.net:8445", "", 8799, "100.2.2.2"))
            self.assertFalse(S.tailnet_user_ok("box.ts.net:8445", "", 8799, ""))

    def test_a_failed_whois_lets_nobody_in(self):
        S._WHOIS.clear()
        with mock.patch.object(S.subprocess, "run", side_effect=OSError("no tailscale")):
            self.assertEqual(set(), S.peer_tags("100.9.9.9"))

    def test_the_unit_carries_the_tags(self):
        rec = {"publish_hosts": "box.ts.net", "publish_users": "owner@example.com", "publish_tags": "tag:admin"}
        with mock.patch.object(CI, "_owner_record", return_value=rec):
            self.assertIn("Environment=CREW_GRAPH_TAGS=tag:admin\n", CI.render_graph_unit("/p"))


class PublishSettingsTests(unittest.TestCase):
    def test_the_one_human_login_is_the_default(self):
        with mock.patch.object(CI, "_ts_humans", return_value=["owner@example.com"]):
            self.assertEqual(("box.ts.net", "owner@example.com", ""), CI.publish_settings("box.ts.net"))

    def test_two_humans_and_no_flag_is_refused_not_guessed(self):
        with mock.patch.object(CI, "_ts_humans", return_value=["a@x.com", "b@x.com"]):
            self.assertIn("--publish-user", CI.publish_settings("box.ts.net")[2])

    def test_the_flag_wins_and_no_tailscale_is_refused(self):
        self.assertEqual("b@x.com", CI.publish_settings("box.ts.net", "b@x.com")[1])
        self.assertTrue(CI.publish_settings("", "b@x.com")[2])

    def test_the_unit_carries_hosts_and_users_once_published(self):
        with mock.patch.object(CI, "_owner_record", return_value={"publish_hosts": "box.ts.net,box.ts.net:8445",
                                                                  "publish_users": "owner@example.com"}):
            unit = CI.render_graph_unit("/p")
        self.assertIn("Environment=CREW_GRAPH_HOSTS=box.ts.net,box.ts.net:8445\n", unit)
        self.assertIn("Environment=CREW_GRAPH_USERS=owner@example.com\n", unit)
        with mock.patch.object(CI, "_owner_record", return_value={}):
            self.assertNotIn("CREW_GRAPH_USERS", CI.render_graph_unit("/p"))


if __name__ == "__main__":
    unittest.main()
