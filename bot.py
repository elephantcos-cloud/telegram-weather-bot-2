import os
import sys
import time
import requests

BOT_TOKEN     = os.environ["BOT_TOKEN"]
CHAT_ID       = os.environ["CHAT_ID"]
WEATHER_KEY   = os.environ["WEATHER_API_KEY"]
NEWS_KEY      = os.environ["NEWS_API_KEY"]
CITY          = os.environ.get("CITY", "Dhaka")
OFFSET_FILE   = "offset.txt"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    resp = requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML"
    })
    if not resp.ok:
        print(f"[ERROR] sendMessage failed: {resp.text}")

def get_weather():
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={CITY}&appid={WEATHER_KEY}&units=metric"
    )
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        return f"❌ Weather fetch error: {e}"
    if data.get("cod") != 200:
        return f"❌ Weather পাওয়া যায়নি।"
    name     = data["name"]
    desc     = data["weather"][0]["description"].title()
    temp     = data["main"]["temp"]
    feels    = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind     = data["wind"]["speed"]
    icon_map = {"clear":"☀️","cloud":"☁️","rain":"🌧️","drizzle":"🌦️","thunder":"⛈️","snow":"❄️","mist":"🌫️","fog":"🌫️","haze":"🌫️"}
    icon = next((v for k, v in icon_map.items() if k in desc.lower()), "🌤️")
    return (
        f"{icon} <b>আবহাওয়া — {name}</b>\n\n"
        f"🌡 তাপমাত্রা : <b>{temp:.1f}°C</b>  (অনুভব {feels:.1f}°C)\n"
        f"☁️ অবস্থা    : {desc}\n"
        f"💧 আর্দ্রতা  : {humidity}%\n"
        f"💨 বাতাস     : {wind} m/s"
    )

def get_news():
    url = (
        f"https://newsapi.org/v2/top-headlines"
        f"?country=us&apiKey={NEWS_KEY}&pageSize=5"
    )
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        return f"❌ News fetch error: {e}"
    articles = data.get("articles", [])
    if not articles:
        return "❌ সংবাদ পাওয়া যায়নি।"
    lines = ["📰 <b>আজকের শীর্ষ সংবাদ</b>\n"]
    for i, article in enumerate(articles[:5], 1):
        title = (article.get("title") or "").split(" - ")[0].strip()
        url_  = article.get("url", "")
        if title:
            lines.append(f"{i}. <a href='{url_}'>{title}</a>")
    return "\n".join(lines)

def send_once():
    print("[INFO] Sending weather + news...")
    send_message(CHAT_ID, get_weather())
    send_message(CHAT_ID, get_news())
    print("[INFO] Done.")

def send_loop(interval_minutes=10, duration_minutes=350):
    print(f"[INFO] Loop mode: every {interval_minutes} min for {duration_minutes} min")
    end_time = time.time() + duration_minutes * 60
    count = 0
    while time.time() < end_time:
        count += 1
        print(f"[INFO] Send #{count}")
        send_once()
        remaining = end_time - time.time()
        sleep_sec = interval_minutes * 60
        if remaining <= sleep_sec:
            break
        print(f"[INFO] Sleeping {interval_minutes} min...")
        time.sleep(sleep_sec)
    print("[INFO] Loop finished.")

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            return int(open(OFFSET_FILE).read().strip())
        except:
            pass
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

HELP_TEXT = (
    "👋 <b>Weather &amp; News Bot</b>\n\n"
    "📌 <b>Commands:</b>\n"
    "/weather — আবহাওয়া দেখো\n"
    "/news    — সর্বশেষ সংবাদ\n"
    "/help    — সাহায্য"
)

def poll_commands():
    offset = load_offset()
    try:
        resp = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=15
        ).json()
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    for update in resp.get("result", []):
        offset = update["update_id"] + 1
        msg = update.get("message")
        if not msg:
            continue
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        if text in ("/start", "/help"):
            send_message(chat_id, HELP_TEXT)
        elif text == "/weather":
            send_message(chat_id, get_weather())
        elif text == "/news":
            send_message(chat_id, get_news())
    save_offset(offset)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "poll"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    if mode == "loop":
        send_loop(interval_minutes=interval)
    elif mode == "schedule":
        send_once()
    else:
        poll_commands()
