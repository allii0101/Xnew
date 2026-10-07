#!/bin/bash
# Runs the X watcher in a loop on your own computer (home IP is usually not blocked by X).
cd "$(dirname "$0")"
if [ ! -f .env ]; then echo "Missing .env file (copy .env.example to .env and fill it)"; exit 1; fi
set -a; source .env; set +a
python3 -m pip install -q twscrape requests
while true; do
  rm -f accounts.db
  python3 watch.py
  sleep 1800
done
