import json
import os

with open(os.path.join(os.path.dirname(__file__), 'data.json')) as f:
    global_data = json.load(f)


class DataProvider:
    def __init__(self) -> None:
        self.data = global_data

    def get_api_key(self) -> str:
        return self.data.get("access_key")

    def get_telegram_token(self):
        return self.data["TELEGRAM"]["TOKEN"]

    def get_telegram_chat_id(self):
        return self.data["TELEGRAM"]["CHAT_ID"]
