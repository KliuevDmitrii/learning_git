from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import time
import urllib.parse
import urllib.request

config = ConfigProvider()
url_base = config.get_exchange_url_base()
base_currency = config.get_base_currency()
target_currency = config.get_target_currency()

url = f"{url_base}?base={base_currency}&symbols={target_currency}"
print(f"URL used: {url}")

dp = DataProvider()
access_key = dp.get_api_key()

max_threshold = config.get_exchange_threshold()
min_threshold = config.get_exchange_min_threshold()

def send_telegram(msg):
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

def get_usd_rate():
    headers = {"apikey": access_key}
    r = requests.get(url, headers=headers, timeout=10)

    data = r.json()

    if data.get("rates") and target_currency in data["rates"]:
        return data["rates"][target_currency]
    else:
        print("Ошибка от API:", data.get("error", "Нет поля 'rates'"))
        return None

while True:
    rate = get_usd_rate()
    # print(f'{base_currency}/{target_currency}: {rate}')

    if rate is None:
        print("Курс не получен. Ждём 60 сек.")
        time.sleep(60)
        continue

    if rate > max_threshold:
        message = f'Курс {base_currency}/{target_currency} превысил максимально установленный {max_threshold}: {rate}'
        print(message)
        send_telegram(message)
        break
    elif rate < min_threshold:
        message = f'Курс {base_currency}/{target_currency} ниже минимально установленного {min_threshold}: {rate}'
        print(message)
        send_telegram(message)
        break
    else:
        print(f'Курс в пределах допустимого диапазона: {min_threshold} ≤ {rate} ≤ {max_threshold}')
        break

    time.sleep(60)
    