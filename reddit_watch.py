"""Watch Reddit hiring subs for video-editor jobs and send the link to Telegram."""
import json, os, re, sys, time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import requests

TG_TOKEN = os.environ["TG_TOKEN"].strip()
TG_CHAT = os.environ["TG_CHAT"].strip()
try:
    from zoneinfo import ZoneInfo
    CAIRO = ZoneInfo("Africa/Cairo")
except Exception:
    CAIRO = timezone(timedelta(hours=3))

# hiring-oriented subs
SUBS = "forhire+hiring+DesignJobs+VideoEditing+slavelabour+freelance_forhire+jobbit+HireaFreelancer+NewTubers+PartneredYoutube"
FEED = f"https://www.reddit.com/r/{SUBS}/new/.rss?limit=100"
STATE_FILE = "reddit_state.json"
FRESH_MINUTES = int(os.environ.get("FRESH_MINUTES", "90"))
ALERT_EVERY_HOURS = 12

ROLE = re.compile(r"video[\s-]*edit|editor|reels?\b|montage|youtube|shorts|clips?\b|motion graphic|مونتير", re.I)
INTENT = re.compile(r"\[hiring\]|hiring|looking for|need|wanted|seeking|recruit|paid|\$|budget|مطلوب", re.I)
OFFER = re.compile(r"\[for hire\]|for hire|hire me|available for|open for (work|commission)|my services|\[offer\]", re.I)

NS = {"a": "http://www.w3.org/2005/Atom"}


def tg(text):
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text}, timeout=20)
    r.raise_for_status()


def load():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"seen": [], "last_alert": 0}


def save(s):
    s["seen"] = s["seen"][-1500:]
    json.dump(s, open(STATE_FILE, "w"))


def fetch():
    r = requests.get(FEED, timeout=30, headers={"User-Agent": "linux:xnew-job-alerts:v1.0 (personal job alerts)"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    for e in root.findall("a:entry", NS):
        title = (e.findtext("a:title", "", NS) or "").strip()
        body = re.sub(r"<[^>]+>", " ", e.findtext("a:content", "", NS) or "")
        link = e.find("a:link", NS).attrib.get("href", "")
        when = e.findtext("a:published", None, NS) or e.findtext("a:updated", "", NS)
        yield e.findtext("a:id", link, NS), title, body, link, datetime.fromisoformat(when.replace("Z", "+00:00"))


def main():
    st = load()
    seen = set(st["seen"])
    try:
        items = list(fetch())
    except Exception as ex:
        if time.time() - st.get("last_alert", 0) > ALERT_EVERY_HOURS * 3600:
            tg(f"⚠️ مراقبة ريديت وقفت: {type(ex).__name__}: {str(ex)[:150]}")
            st["last_alert"] = time.time()
            save(st)
        print("error:", ex)
        sys.exit(1)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=FRESH_MINUTES)
    sent = 0
    for pid, title, body, link, when in sorted(items, key=lambda x: x[4]):
        if pid in seen or when < cutoff:
            continue
        text = f"{title} {body[:600]}"
        if OFFER.search(title) or not ROLE.search(text) or not INTENT.search(title + " " + body[:300]):
            continue
        seen.add(pid)
        mins = max(0, int((datetime.now(timezone.utc) - when).total_seconds() // 60))
        ago = f"{mins} دقيقة" if mins < 60 else f"{mins // 60} ساعة و{mins % 60} دقيقة"
        tg(f"🕒 {when.astimezone(CAIRO).strftime('%Y-%m-%d %I:%M %p')} (من {ago})\n{link}")
        sent += 1
    st["seen"] = list(seen)
    save(st)
    print(f"fetched={len(items)} sent={sent}")


if __name__ == "__main__":
    main()
