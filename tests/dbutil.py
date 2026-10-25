"""Per-test isolated Postgres schema. Set TEST_DATABASE_URL to a throwaway database
(NEVER the production DATABASE_URL). Tests are skipped, loudly, if it is unset."""

import atexit
import os
import unittest
import uuid

from core import db

URL = os.environ.get("TEST_DATABASE_URL", "")
_schemas = []


def require_db():
    if not URL:
        raise unittest.SkipTest("TEST_DATABASE_URL not set; Postgres tests skipped")


def make_conn():
    require_db()
    schema = "t_" + uuid.uuid4().hex[:10]
    admin = db.connect(URL)
    admin.execute(f'CREATE SCHEMA "{schema}"')
    admin.close()
    _schemas.append(schema)
    conn = db.connect(URL, schema=schema)
    db.migrate(conn)
    return conn


@atexit.register
def _cleanup():
    if not _schemas:
        return
    admin = db.connect(URL)
    for s in _schemas:
        admin.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE')
    admin.close()
