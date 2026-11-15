import json
import os

class DataProvider:

    def __init__(self) -> None:
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        try:
            with open(path, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}
        if not isinstance(self.data, dict) or not isinstance(self.data.get("TELEGRAM", {}), dict):
            raise ValueError("data.json должен содержать объект с настройками TELEGRAM")

    def get_api_key(self):
        return os.environ.get("APILAYER_API_KEY") or self.data.get("access_key")

    def get_telegram_token(self):
        return os.environ.get("TELEGRAM_TOKEN") or self.data.get("TELEGRAM", {}).get("TOKEN")

    def get_telegram_chat_id(self):
        return os.environ.get("TELEGRAM_CHAT_ID") or self.data.get("TELEGRAM", {}).get("CHAT_ID")
