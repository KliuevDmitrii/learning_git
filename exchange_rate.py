import requests
import time

def get_usd_rate():
    url = "https://api.exchangerate.host/latest?base=USD&symbols=GEL"
    r = requests.get(url)
    return r.json()['rates']['GEL']

thresold = 2.7 # Set your threshold here
while True:
    rate = get_usd_rate()
    print(f'USD/GEL: {rate}')
    if rate > thresold:
        print(f'Alert! USD/GEL rate has exceeded the threshold of {thresold}. Current rate: {rate}')
        break
    time.sleep(60)  # Check every 60 seconds