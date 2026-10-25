import threading
import unittest

from core import db
from core.queue import queue
from tests import dbutil


def worker_conn(schema_conn):
    schema = schema_conn.execute("select current_schema() s").fetchone()["s"]
    return db.connect(dbutil.URL, schema=schema)


class ConcurrencyTest(unittest.TestCase):
    def run_parallel(self, fn, n):
        out, errs = [None] * n, []
        barrier = threading.Barrier(n)

        def go(i):
            try:
                barrier.wait()
                out[i] = fn(i)
            except Exception as e:  # surfaced below, never swallowed
                errs.append(e)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(n)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        return out

    def test_two_workers_never_claim_the_same_task(self):
        c = dbutil.make_conn()
        for i in range(4):
            queue.enqueue(c, "scout", "scan", f"k{i}")
        conns = [worker_conn(c) for _ in range(8)]
        got = self.run_parallel(lambda i: queue.claim(conns[i], "scout"), 8)
        ids = [r["id"] for r in got if r]
        self.assertEqual(len(ids), 4)
        self.assertEqual(len(set(ids)), 4)  # 8 racers, 4 tasks, no duplicates

    def test_concurrent_enqueue_same_key_creates_one_task(self):
        c = dbutil.make_conn()
        conns = [worker_conn(c) for _ in range(8)]
        ids = self.run_parallel(lambda i: queue.enqueue(conns[i], "scout", "scan", "same"), 8)
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(c.execute("select count(*) from tasks").fetchone()[0], 1)

    def test_concurrent_migrate_is_safe(self):
        dbutil.require_db()
        import uuid
        schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{schema}"')
        dbutil._schemas.append(schema)
        conns = [db.connect(dbutil.URL, schema=schema) for _ in range(5)]
        applied = self.run_parallel(lambda i: db.migrate(conns[i]), 5)
        names = [n for a in applied for n in a]
        self.assertEqual(sorted(names), sorted(f.name for f in db.MIGRATIONS.glob("*.sql")))  # each applied exactly once


if __name__ == "__main__":
    unittest.main()
