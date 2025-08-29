from ConfigProvider import ConfigProvider
from DataProvider import DataProvider
import requests
import time

config = ConfigProvider()
url = config.get_exchange_url()

dp = DataProvider()
access_key = dp.get_api_key()

def get_usd_rate():
    try:
        headers = {"apikey": access_key}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        print("🔎 Ответ API:", data)

        if "rates" in data and "GEL" in data["rates"]:
            return data["rates"]["GEL"]
        else:
            print("Ошибка от API:", data.get("error", "Нет поля 'rates'"))
            return None
    except Exception as e:
        print("Ошибка соединения:", e)
        return None

thresold =  config.get_exchange_threshold()
while True:
    rate = get_usd_rate()
    print(f'USD/GEL: {rate}')

    if rate is None:
        print("Курс не получен. Ждём 60 сек.")
        time.sleep(60)
        continue

    if rate > thresold:
        print(f'Alert! USD/GEL rate has exceeded the threshold of {thresold}. Current rate: {rate}')
        break
    time.sleep(60)  # Check every 60 seconds
    