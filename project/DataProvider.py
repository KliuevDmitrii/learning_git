import json
import os

class DataProvider:

    def __init__(self) -> None:
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(path, 'r') as f:
            self.data = json.load(f)

    def get_api_key(self):
        return self.data.get("access_key")

    def get_telegram_token(self):
        return self.data.get("TELEGRAM", {}).get("TOKEN")

    def get_telegram_chat_id(self):
        return self.data.get("TELEGRAM", {}).get("CHAT_ID")
