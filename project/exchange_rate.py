from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import urllib.parse
import urllib.request
import time
import json
import os

config = ConfigProvider()
url = config.get_exchange_url()
print(f"URL used: {url}")

dp = DataProvider()
max_threshold = config.get_exchange_threshold()
min_threshold = config.get_exchange_min_threshold()

LAST_RATE_FILE = os.path.join(os.path.dirname(__file__), "last_rate.json")


# ---------- Работа с Telegram ----------
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
            result = response.read()
            print("Уведомление отправлено:", result)
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)


# ---------- Работа с last_rate ----------
def load_last_rate():
    if not os.path.exists(LAST_RATE_FILE):
        return None
    try:
        with open(LAST_RATE_FILE, "r") as f:
            return json.load(f).get("last_rate")
    except:
        return None


def save_last_rate(rate):
    with open(LAST_RATE_FILE, "w") as f:
        json.dump({"last_rate": rate}, f)


# ---------- Получение курса ----------
def get_usd_rate(max_retries=3, retry_delay=60):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Попытка {attempt}] Запрашиваем курс...")

            r = requests.get(url, timeout=10)
            data = r.json()

            print("🔎 Ответ API:", data)

            if "rates" in data and config.get_target_currency() in data["rates"]:
                return data["rates"][config.get_target_currency()]
            else:
                print("Ошибка от API: Нет поля 'rates'")
                send_telegram(f"❌ API вернул ошибку или пустые данные. Ответ: {data}")
                return None

        except requests.exceptions.ReadTimeout:
            print(f"⏳ Таймаут ({attempt}/{max_retries})")
            send_telegram(f"⏳ Таймаут при запросе ({attempt}/{max_retries})")

        except Exception as e:
            print(f"Ошибка: {e}")
            send_telegram(f"⚠️ Ошибка: {e}")

        if attempt < max_retries:
            print(f"Ждём {retry_delay} сек...\n")
            time.sleep(retry_delay)

    send_telegram("❌ Все попытки получить курс не удались.")
    return None


# ---------- Главная логика ----------
current_rate = get_usd_rate()
if current_rate is None:
    print("Курс не получен. Завершение.")
    exit(1)

last_rate = load_last_rate()

if last_rate is None:
    message = f"Первый запуск. Текущий курс: {current_rate}"
    save_last_rate(current_rate)
    print(message)
    send_telegram(message)
    exit(0)

# ----------- Сравнение ----------
difference = current_rate - last_rate

if difference > 0:
    trend = "📈 Курс повысился"
elif difference < 0:
    trend = "📉 Курс понизился"
else:
    trend = "➖ Курс не изменился"

message = (
    f"{trend}\n\n"
    f"📊 Прошлый курс: {last_rate}\n"
    f"📊 Текущий курс: {current_rate}\n"
    f"Δ Разница: {difference:.4f}"
)

print(message)
send_telegram(message)

# сохраняем текущий курс как прошлый
save_last_rate(current_rate)