"""LinkedIn public (guest) job search -> Telegram. No login, no cookies."""
import html, json, os, re, sys, time
from urllib.parse import quote
import requests

TG_TOKEN = os.environ["TG_TOKEN"].strip()
TG_CHAT = os.environ["TG_CHAT"].strip()
FRESH_MINUTES = int(os.environ.get("FRESH_MINUTES", "90"))
STATE_FILE = "linkedin_state.json"
ALERT_EVERY_HOURS = 12

KEYWORDS = ["video editor", "reels editor", "short form video editor", "motion graphics", "مونتير"]
# (label, extra query params): remote worldwide, and Egypt
PLACES = [("remote", "&location=Worldwide&f_WT=2"), ("egypt", "&location=Egypt")]
BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


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


def search(keyword, extra):
    secs = max(FRESH_MINUTES, 30) * 60
    url = f"{BASE}?keywords={quote(keyword)}{extra}&f_TPR=r{secs}&sortBy=DD&start=0"
    r = requests.get(url, timeout=30, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    r.raise_for_status()
    out = []
    for card in re.split(r"<li>", r.text)[1:]:
        m = re.search(r'href="(https://[a-z.]*linkedin\.com/jobs/view/[^"?]+)', card)
        if not m:
            continue
        link = html.unescape(m.group(1))
        jid = re.search(r"(\d{6,})/?$", link)
        title = re.search(r'base-search-card__title[^>]*>\s*(.*?)\s*<', card, re.S)
        when = re.search(r'job-search-card__listdate[^>]*>\s*(.*?)\s*<', card, re.S)
        out.append((jid.group(1) if jid else link, link,
                    html.unescape(title.group(1)) if title else "", html.unescape(when.group(1)) if when else ""))
    return out


def main():
    st = load()
    seen = set(st["seen"])
    fetched = sent = 0
    errors = []
    for kw in KEYWORDS:
        for label, extra in PLACES:
            try:
                for jid, link, title, when in search(kw, extra):
                    fetched += 1
                    if jid in seen:
                        continue
                    seen.add(jid)
                    tg(f"💼 {title}\n🕒 {when or 'حديث'}\n{link}")
                    sent += 1
            except Exception as ex:
                errors.append(f"{kw}/{label}: {type(ex).__name__} {str(ex)[:80]}")
            time.sleep(2)
    st["seen"] = list(seen)
    if errors and fetched == 0 and time.time() - st.get("last_alert", 0) > ALERT_EVERY_HOURS * 3600:
        try:
            tg("⚠️ مراقبة لينكدإن وقفت: " + errors[0])
            st["last_alert"] = time.time()
        except Exception:
            pass
    save(st)
    print(f"li_fetched={fetched} li_sent={sent} errors={len(errors)}")
    if errors:
        print("li_errors:", "; ".join(errors[:3]))


if __name__ == "__main__":
    main()
