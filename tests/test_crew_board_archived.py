"""board_data's Archived lane: last, the newest ARCHIVED_SHOWN with the rest counted, crew cards only, and kept
out of the live counts. Needs the Hermes venv python (tests/kernel_board.py)."""
import importlib.util
import os
import tempfile
import unittest

from tests import kernel_board as kbd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def serve():
    spec = importlib.util.spec_from_file_location("cgs_archived", os.path.join(HERE, "scripts", "crew_graph_serve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ArchivedLane(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = {k: os.environ.get(k) for k in ("KANBAN_DB", "HERMES_KANBAN_DB")}
        self.addCleanup(self.restore)
        kb, self.conn, path = kbd.open_board(self.tmp.name)
        os.environ["KANBAN_DB"] = path
        self.mod = serve()
        self.live = kbd.add_card(self.conn, title="live card")

    def restore(self):
        for k, v in self.saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def archive(self, title, n=1, at=None):
        ids = []
        for i in range(n):
            cid = kbd.add_card(self.conn, title="%s %d" % (title, i))
            self.conn.execute("update tasks set status='archived', created_at=? where id=?",
                              (at + i if at else 1000 + i, cid))
            ids.append(cid)
        self.conn.commit()
        return ids

    def lane(self, **kw):
        lanes = self.mod.board_data(**kw)["lanes"]
        return lanes, {l["key"]: l for l in lanes}["archived"]

    def test_last_lane_and_empty_when_nothing_archived(self):
        lanes, arch = self.lane()
        self.assertEqual("archived", lanes[-1]["key"])
        self.assertEqual((0, 0), (len(arch["tiles"]), arch["hidden"]))

    def test_bounded_newest_first_with_the_total_in_hidden(self):
        n = self.mod.ARCHIVED_SHOWN + 5
        ids = self.archive("old", n)
        data = self.mod.board_data()
        arch = data["lanes"][-1]
        self.assertEqual(self.mod.ARCHIVED_SHOWN, len(arch["tiles"]))
        self.assertEqual(n, len(arch["tiles"]) + arch["hidden"])
        self.assertEqual(ids[-1], arch["tiles"][0]["id"])            # newest created_at first
        self.assertNotIn(ids[0], [t["id"] for t in arch["tiles"]])    # the oldest fell off
        self.assertTrue(all("summary" in t and "verdict" in t for t in arch["tiles"]))

    def test_archived_never_enter_counts_cards_or_live_lanes(self):
        ids = self.archive("gone", 3)
        data = self.mod.board_data()
        self.assertNotIn("archived", data["counts"])
        self.assertEqual(1, data["cards"])
        live = [t["id"] for l in data["lanes"] if l["key"] != "archived" for t in l["tiles"]]
        self.assertEqual([self.live], live)
        self.assertTrue(set(ids) <= {t["id"] for t in data["lanes"][-1]["tiles"]})

    def test_probe_cards_only_with_show_all(self):
        self.archive("PROBE scaffolding", 2)
        real = self.archive("real", 1)
        _, plain = self.lane()
        self.assertEqual(real, [t["id"] for t in plain["tiles"]])
        _, every = self.lane(include_all=True)
        self.assertEqual(3, len(every["tiles"]) + every["hidden"])


if __name__ == "__main__":
    unittest.main()
