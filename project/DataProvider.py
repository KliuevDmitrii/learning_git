import json
import os

with open(os.path.join(os.path.dirname(__file__), 'data.json')) as f:
    global_data = json.load(f)

class DataProvider:
    def __init__(self) -> None:
        self.data = global_data

    def get_api_key(self) -> str:
        return self.data.get("apikey")