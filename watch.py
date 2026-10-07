import asyncio, json, os, time
from datetime import datetime, timezone, timedelta

import requests
from twscrape import API

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT = os.environ["TG_CHAT"]
X_USERNAME = os.environ["X_USERNAME"]
X_COOKIES = os.environ["X_COOKIES"]  # "auth_token=...; ct0=..."

QUERY = os.environ.get("X_QUERY") or (
    '("need video editor" OR "hiring video editor" OR "video editor wanted" '
    'OR "looking for video editor" OR "looking for a video editor" '
    'OR "need a video editor" OR "hiring a video editor" OR "مطلوب مونتير") '
    "-filter:replies -filter:retweets"
)
FRESH_MINUTES = 20          # ignore tweets older than this (avoids flooding on first run)
ALERT_EVERY_HOURS = 12      # how often to repeat a "monitoring is broken" alert
STATE_FILE = "state.json"


def tg(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": False},
        timeout=20,
    )
    r.raise_for_status()


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen": [], "last_alert": 0}


def save_state(state):
    state["seen"] = state["seen"][-1000:]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


async def main():
    state = load_state()
    seen = set(state["seen"])
    api = API("accounts.db")
    await api.pool.add_account(X_USERNAME, "unused", "unused@example.com", "unused", cookies=X_COOKIES)

    try:
        tweets = []
        async for t in api.search(QUERY, limit=40, kv={"product": "Latest"}):
            tweets.append(t)
    except Exception as e:
        if time.time() - state.get("last_alert", 0) > ALERT_EVERY_HOURS * 3600:
            tg(f"⚠️ مراقبة تويتر وقفت: {type(e).__name__}: {str(e)[:200]}\nغالباً الكوكيز انتهت أو X رفض الدخول.")
            state["last_alert"] = time.time()
            save_state(state)
        raise

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=FRESH_MINUTES)
    sent = 0
    for t in sorted(tweets, key=lambda x: x.date):
        tid = str(t.id)
        if tid in seen:
            continue
        seen.add(tid)
        if t.date < cutoff:
            continue
        text = (t.rawContent or "").strip().replace("\n", " ")[:300]
        tg(f"🎬 @{t.user.username}\n{text}\n\n{t.url}")
        sent += 1

    state["seen"] = list(seen)
    save_state(state)
    print(f"fetched={len(tweets)} sent={sent}")


if __name__ == "__main__":
    asyncio.run(main())
