#!/bin/bash
# One-time setup on macOS: installs deps and schedules a check every 30 minutes.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
[ -f .env ] || { echo "Create .env first (cp .env.example .env and fill it)"; exit 1; }
PY=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3)
VER=$($PY -c 'import sys;print("%d.%d"%sys.version_info[:2])')
$PY -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "Python $VER is too old. Run: brew install python@3.12  then run this again."; exit 1; }
[ -d .venv ] || $PY -m venv .venv
./.venv/bin/pip install -q twscrape requests
chmod +x run_once.sh
PLIST="$HOME/Library/LaunchAgents/com.xnew.watch.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.xnew.watch</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$DIR/run_once.sh</string></array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/watch.log</string>
  <key>StandardErrorPath</key><string>$DIR/watch.log</string>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
echo "Done. A check runs now and then every 30 minutes. Log: $DIR/watch.log"
echo "To stop: launchctl unload $PLIST"
