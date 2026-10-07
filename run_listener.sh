#!/bin/bash
# Keeps listening for /check on Telegram (started by launchd).
cd "$(dirname "$0")"
[ -f .env ] || { echo "Missing .env"; exit 1; }
set -a; source .env; set +a
exec ./.venv/bin/python listener.py
