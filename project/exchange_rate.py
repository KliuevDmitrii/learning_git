from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import urllib.parse
import urllib.request
import time

config = ConfigProvider()
url = config.get_exchange_url()
print(f"URL used: {url}")

dp = DataProvider()
max_threshold = config.get_exchange_threshold()
min_threshold = config.get_exchange_min_threshold()


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


def get_usd_rate(max_retries=3, retry_delay=60):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Попытка {attempt}] Запрашиваем курс...")

            r = requests.get(url, timeout=10)
            data = r.json()

            # 🔎 Отладка: выводим ответ API
            print("🔎 Ответ API:", data)

            if "rates" in data and config.get_target_currency() in data["rates"]:
                return data["rates"][config.get_target_currency()]
            else:
                print("Ошибка от API: Нет поля 'rates'")
                send_telegram(f"❌ API вернул ошибку или пустые данные. Ответ: {data}")
                return None

        except requests.exceptions.ReadTimeout:
            print(f"⏳ Таймаут при запросе ({attempt}/{max_retries})")
            send_telegram(f"⏳ Таймаут при запросе курса ({attempt}/{max_retries})")

        except Exception as e:
            print(f"Ошибка при получении курса: {e}")
            send_telegram(f"⚠️ Ошибка при получении курса: {e}")

        if attempt < max_retries:
            print(f"Ждём {retry_delay} сек перед следующей попыткой...\n")
            time.sleep(retry_delay)

    print("❌ Все попытки не удались.")
    send_telegram("❌ Все попытки получить курс завершились неудачно.")
    return None


rate = get_usd_rate()

if rate is None:
    print("Курс не получен. Завершение работы.")
    exit(1)

if rate > max_threshold:
    message = (
        f'📈 Курс {config.get_base_currency()}/{config.get_target_currency()} '
        f'превысил максимум {max_threshold}: {rate}'
    )
elif rate < min_threshold:
    message = (
        f'📉 Курс {config.get_base_currency()}/{config.get_target_currency()} '
        f'ниже минимума {min_threshold}: {rate}'
    )
else:
    message = (
        f'✅ Курс в пределах нормы: '
        f'{min_threshold} ≤ {rate} ≤ {max_threshold}'
    )

print(message)
send_telegram(message)

