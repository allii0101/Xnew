"""Telegram command listener: send /check to the bot to run a scan right now."""
import os, re, subprocess, time
import requests

TOKEN = os.environ["TG_TOKEN"]
CHAT = str(os.environ["TG_CHAT"]).strip()
API = f"https://api.telegram.org/bot{TOKEN}"
HERE = os.path.dirname(os.path.abspath(__file__))
TRIGGERS = ("/check", "/start", "check", "فحص", "شيك", "دور")


def call(method, **kw):
    r = requests.post(f"{API}/{method}", json=kw, timeout=70)
    return r.json()


def say(text):
    try:
        call("sendMessage", chat_id=CHAT, text=text)
    except Exception:
        pass


def run_scan():
    env = dict(os.environ, FRESH_MINUTES="180")  # manual check looks back 3h
    try:
        p = subprocess.run(["/bin/bash", os.path.join(HERE, "run_once.sh")],
                           capture_output=True, text=True, timeout=240, env=env)
    except subprocess.TimeoutExpired:
        return "⚠️ الفحص اتأخر أكتر من اللازم، جرب كمان شوية."
    out = (p.stdout or "") + (p.stderr or "")
    if "busy" in out and "fetched=" not in out:
        return "⏳ فحص تاني شغال دلوقتي، جرب بعد دقيقة."
    m = re.search(r"fetched=(\d+) sent=(\d+)", out)
    if p.returncode == 0 and m:
        n = int(m.group(2))
        return f"✅ خلص الفحص. جديد: {n}" if n else "✅ خلص الفحص. مفيش تويتات جديدة دلوقتي."
    return "⚠️ الفحص فشل:\n" + out.strip()[-300:]


def main():
    call("deleteWebhook")
    try:
        call("setMyCommands", commands=[{"command": "check", "description": "افحص X دلوقتي"}])
    except Exception:
        pass
    offset = None
    try:  # skip anything sent before we started
        r = call("getUpdates", offset=-1, timeout=0).get("result", [])
        if r:
            offset = r[-1]["update_id"] + 1
    except Exception:
        pass
    while True:
        try:
            kw = {"timeout": 50}
            if offset:
                kw["offset"] = offset
            res = call("getUpdates", **kw)
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                if str(msg.get("chat", {}).get("id")) != CHAT:
                    continue
                text = (msg.get("text") or "").strip().lower()
                if any(text.startswith(t) for t in TRIGGERS):
                    say("🔎 بفحص X دلوقتي...")
                    say(run_scan())
        except Exception:
            time.sleep(10)


if __name__ == "__main__":
    main()
