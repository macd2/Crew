"""Role faces: a role is given one of the shipped faces on first use and keeps it; the URL never names a file."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import crew_graph_serve as S  # noqa: E402


class FaceSetTests(unittest.TestCase):
    def test_the_shipped_set_is_ten_faces(self):
        self.assertEqual(["blobs-%02d.svg" % i for i in range(1, 11)], S.face_files())


class RoleFaceTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="crew-faces-")
        p = mock.patch.object(S.CG.crew_card, "base_home", lambda: self.home)
        p.start()
        self.addCleanup(p.stop)

    def test_a_role_keeps_its_face_and_the_choice_is_saved(self):
        first = S.role_face("worker")
        self.assertIn(first, S.face_files())
        self.assertEqual(first, S.role_face("worker"))
        self.assertEqual(first, S.role_face("crew-worker"))                 # crew-<role> is <role>
        with open(os.path.join(self.home, "crew", "faces.json")) as fh:
            self.assertEqual(first, json.load(fh)["worker"])

    def test_the_four_roles_get_four_different_faces(self):
        got = [S.role_face(r) for r in ("coordinator", "worker", "content", "verifier")]
        self.assertEqual(4, len(set(got)))

    def test_a_saved_choice_survives_a_restart(self):
        os.makedirs(os.path.join(self.home, "crew"))
        with open(os.path.join(self.home, "crew", "faces.json"), "w") as fh:
            json.dump({"verifier": "blobs-07.svg"}, fh)
        self.assertEqual("blobs-07.svg", S.role_face("verifier"))

    def test_the_url_names_a_role_never_a_file(self):
        for p in ("/avatars/role/../crew_card.py.svg", "/avatars/blobs-01.svg", "/avatars/role/a/b.svg",
                  "/avatars/role/.svg", "/avatars/role/Worker.svg"):
            self.assertIsNone(S.FACE_RX.match(p), p)
        self.assertEqual("worker", S.FACE_RX.match("/avatars/role/worker.svg").group(1))


if __name__ == "__main__":
    unittest.main()
