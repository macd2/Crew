"""The proofs' board connection retries a transient lock fault and nothing else."""
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import crew_proof_board  # noqa: E402


class RetryingConnection(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "b.db")
        conn = crew_proof_board.connect(self.db)
        conn.execute("create table t (x)")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.dir.cleanup()

    def _failing(self, conn, message, times):
        left = [times]

        def run(sql):
            if left[0] > 0:
                left[0] -= 1
                raise sqlite3.OperationalError(message)
            return sqlite3.Connection.execute(conn, sql)
        return run, left

    def test_locking_protocol_is_retried_until_the_statement_runs(self):
        conn = crew_proof_board.connect(self.db)
        try:
            run, left = self._failing(conn, "locking protocol", 3)
            with mock.patch.object(crew_proof_board.time, "sleep", lambda s: None):
                conn._again(run, "insert into t values (1)")
            conn.commit()
            self.assertEqual(conn.execute("select count(*) from t").fetchone()[0], 1)
            self.assertEqual(left[0], 0)
        finally:
            conn.close()

    def test_a_fault_that_never_clears_still_fails(self):
        conn = crew_proof_board.connect(self.db)
        try:
            run, _ = self._failing(conn, "locking protocol", 99)
            with mock.patch.object(crew_proof_board.time, "sleep", lambda s: None):
                with self.assertRaises(sqlite3.OperationalError):
                    conn._again(run, "insert into t values (1)")
        finally:
            conn.close()

    def test_a_real_fault_is_not_retried(self):
        conn = crew_proof_board.connect(self.db)
        try:
            run, left = self._failing(conn, "no such table: nope", 5)
            with self.assertRaises(sqlite3.OperationalError):
                conn._again(run, "select * from nope")
            self.assertEqual(left[0], 4)
        finally:
            conn.close()

    def test_execute_and_commit_go_through_the_retry(self):
        conn = crew_proof_board.connect(self.db)
        try:
            seen = []
            with mock.patch.object(type(conn), "_again", lambda self_, call, *a: seen.append(call.__name__) or call(*a)):
                conn.execute("insert into t values (2)")
                conn.commit()
            self.assertEqual(seen, ["execute", "commit"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
