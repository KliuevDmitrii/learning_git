from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import time

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
    print(f'{base_currency}/{target_currency}: {rate}')

    if rate is None:
        print("Курс не получен. Ждём 60 сек.")
        time.sleep(60)
        continue

    if rate > max_threshold:
        print(f'Курс превысил верхний порог: {rate} > {max_threshold}')
        break
    elif rate < min_threshold:
        print(f'Курс ниже нижнего порога: {rate} < {min_threshold}')
        break

    time.sleep(60)
    