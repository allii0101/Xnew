#!/bin/bash
# One check. Used by launchd every 30 minutes and by the /check bot command.
cd "$(dirname "$0")"
[ -f .env ] || { echo "Missing .env"; exit 1; }
LOCK=.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  # stale lock (>10 min)? clear it, otherwise another scan is running
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then rmdir "$LOCK"; mkdir "$LOCK" || exit 0
  else echo "busy"; exit 0; fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
set -a; source .env; set +a
rm -f accounts.db
./.venv/bin/python watch.py; RC=$?
./.venv/bin/python linkedin_watch.py || true
exit $RC
