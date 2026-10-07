import asyncio, json, os, time
from datetime import datetime, timezone, timedelta

import requests
try:
    from zoneinfo import ZoneInfo
    CAIRO = ZoneInfo("Africa/Cairo")
except Exception:
    CAIRO = timezone(timedelta(hours=3))
from twscrape import API
from twscrape.logger import set_log_level

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT = os.environ["TG_CHAT"]
X_USERNAME = os.environ["X_USERNAME"]


def _clean(v):
    return (v or "").strip().strip('"').strip("'").replace("\n", "").replace("\r", "").replace(" ", "")


def build_cookies():
    auth, ct0 = _clean(os.environ.get("X_AUTH_TOKEN")), _clean(os.environ.get("X_CT0"))
    if auth and ct0:
        return f"auth_token={auth}; ct0={ct0}"
    raw = (os.environ.get("X_COOKIES") or "").strip()
    if "auth_token=" in raw and "ct0=" in raw:
        return raw
    raise SystemExit(
        "X cookies missing: add secrets X_AUTH_TOKEN and X_CT0 "
        f"(auth_token set={bool(auth)}, ct0 set={bool(ct0)}, X_COOKIES length={len(raw)})"
    )


X_COOKIES = build_cookies()

QUERY = os.environ.get("X_QUERY") or (
    # intent word + role phrase anywhere in the tweet (catches lists like "Looking for: ... Video Editor")
    '(("looking for" OR hiring OR need OR needed OR wanted OR seeking OR recruiting OR "in need of") '
    '("video editor" OR "video editors" OR "reels editor" OR "short form editor")) '
    'OR ("editor needed") OR ("editor wanted") '
    'OR (مونتير (مطلوب OR محتاج OR عايز OR نحتاج OR "ابحث عن")) '
    'OR ("محرر فيديو" مطلوب) '
    # drop editors advertising themselves
    '-"for hire" -"hire me" -"available for" -"open for" -"my services" -"tags :" '
    "-filter:replies -filter:retweets"
)
FRESH_MINUTES = int(os.environ.get("FRESH_MINUTES", "45"))  # ignore tweets older than this (must be > run interval)
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
    set_log_level("INFO")
    api = API("accounts.db")
    await api.pool.add_account(X_USERNAME, "unused", "unused@example.com", "unused", cookies=X_COOKIES)

    async def fetch():
        out = []
        async for t in api.search(QUERY, limit=40, kv={"product": "Latest"}):
            out.append(t)
        return out

    try:
        tweets = await asyncio.wait_for(fetch(), timeout=90)
    except Exception as e:
        if isinstance(e, asyncio.TimeoutError):
            e = RuntimeError("timeout: X not answering (account rate-limited, locked, or cookies rejected)")
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
        if t.date < cutoff:
            continue  # too old for this run; don't mark seen so /check can still find it
        seen.add(tid)
        text = (t.rawContent or "").strip().replace("\n", " ")[:300]
        local = t.date.astimezone(CAIRO)
        mins = max(0, int((datetime.now(timezone.utc) - t.date).total_seconds() // 60))
        ago = f"{mins} دقيقة" if mins < 60 else f"{mins // 60} ساعة و{mins % 60} دقيقة"
        tg(f"🎬 @{t.user.username}\n{text}\n\n"
           f"🕒 نُشر: {local.strftime('%Y-%m-%d %I:%M %p')} (من {ago})\n\n{t.url}")
        sent += 1

    state["seen"] = list(seen)
    save_state(state)
    print(f"fetched={len(tweets)} sent={sent}")


if __name__ == "__main__":
    asyncio.run(main())
