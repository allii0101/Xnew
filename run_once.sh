#!/bin/bash
# One check. Used by the macOS scheduler (launchd) every 30 minutes.
cd "$(dirname "$0")"
[ -f .env ] || { echo "Missing .env"; exit 1; }
set -a; source .env; set +a
rm -f accounts.db
./.venv/bin/python watch.py
