from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import urllib.parse
import urllib.request
import json
import os
import time

config = ConfigProvider()
dp = DataProvider()

url = config.get_exchange_url()
target_currency = config.get_target_currency()

LAST_RATE_FILE = os.path.join(os.path.dirname(__file__), "last_rate.json")

print(f"URL used: {url}")


# ---------- Telegram ----------
def send_telegram(msg: str):
    base_url = config.get_exchange_url_telegram()
    token = dp.get_telegram_token()
    chat_id = dp.get_telegram_chat_id()

    url = f"{base_url}{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": msg
    }).encode()

    try:
        with urllib.request.urlopen(url, data=data) as response:
            print("Уведомление отправлено:", response.read())
    except Exception as e:
        print("Ошибка отправки:", e)


# ---------- Работа с last_rate ----------
def load_last_rate():
    try:
        with open(LAST_RATE_FILE, "r") as f:
            return json.load(f).get("last_rate")
    except:
        return None


def save_last_rate(rate):
    with open(LAST_RATE_FILE, "w") as f:
        json.dump({"last_rate": rate}, f)


# ---------- Получение курса ----------
def get_rate():
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        print("🔎 Ответ API:", data)

        if "rates" in data and target_currency in data["rates"]:
            return data["rates"][target_currency]
        return None
    except Exception as e:
        print("Ошибка:", e)
        return None


# ---------- Основная логика ----------
current_rate = get_rate()

if current_rate is None:
    send_telegram("❌ Не удалось получить курс валюты!")
    exit(1)

last_rate = load_last_rate()

if last_rate is None:
    msg = f"Первый запуск.\nТекущий курс: {current_rate}"
    send_telegram(msg)
    save_last_rate(current_rate)
    print(msg)
    exit(0)

difference = current_rate - last_rate

if difference > 0:
    trend = "📈 Курс вырос"
elif difference < 0:
    trend = "📉 Курс упал"
else:
    trend = "➖ Курс не изменился"

msg = (
    f"{trend}\n\n"
    f"📊 Прошлый курс: {last_rate}\n"
    f"📊 Текущий курс: {current_rate}\n"
    f"Δ Разница: {difference:.4f}"
)

print(msg)
send_telegram(msg)
save_last_rate(current_rate)