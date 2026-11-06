#!/bin/bash
# Resets a THROWAWAY local database and restarts a local app server on it, then writes a fresh owner session token to $TOKEN_FILE.
# Used by capture_demo.js. NEVER point DEMO_DB_URL at a real database: this script DROPS the database named in it.
#   DEMO_DB_ADMIN="postgresql://postgres@localhost:5433/postgres?host=/tmp" DEMO_DB_NAME=z2r_dev TOKEN_FILE=/tmp/e2e_token ./reset_demo_env.sh
set -euo pipefail
: "${DEMO_DB_ADMIN:?admin URL of a LOCAL postgres}" "${DEMO_DB_NAME:?name of the throwaway db}" "${TOKEN_FILE:?where to write the token}"
case "$DEMO_DB_NAME" in z2r_dev|z2r_demo|*_demo|*_dev|*_scratch) ;; *) echo "refusing: $DEMO_DB_NAME does not look like a throwaway database"; exit 2;; esac
PORT="${PORT:-8099}"
pkill -f "serve.port=${PORT}" 2>/dev/null || true; sleep 1
psql "$DEMO_DB_ADMIN" -qc "drop database if exists ${DEMO_DB_NAME}" -c "create database ${DEMO_DB_NAME}" 2>&1 | grep -v NOTICE || true
export DATABASE_URL="$(python3 -c "import sys,urllib.parse as u; p=u.urlsplit(sys.argv[1]); print(u.urlunsplit(p._replace(path='/'+sys.argv[2])))" "$DEMO_DB_ADMIN" "$DEMO_DB_NAME")"
cd "$(dirname "$0")/../.."
(nohup python3 -W ignore -c "from dashboard import app; app.serve(port=${PORT})" > /tmp/demo_server.log 2>&1 &)
sleep 3
python3 -W ignore -c "
import sys; sys.path.insert(0,'.')
from core import db
from tests.authutil import session
open('${TOKEN_FILE}','w').write(session(db.connect())[0])"
[ "$(pgrep -fc "serve.port=${PORT}")" = "1" ] || { echo "expected exactly one server process"; exit 1; }
