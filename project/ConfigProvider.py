import configparser
import os


class ConfigProvider:
    def __init__(self) -> None:
        self.config = configparser.ConfigParser(interpolation=None)
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        if not self.config.read(config_path):
            raise ValueError("Не найден config.ini")

    def get_exchange_url(self):
        return self.config.get("exchange", "url_base")

    def get_poll_interval_seconds(self):
        interval = self.config.getint("exchange", "poll_interval_seconds", fallback=60)
        if interval < 1:
            raise ValueError("poll_interval_seconds должен быть не меньше 1")
        return interval

    def get_base_currency(self):
        return self.config.get("exchange", "base_currency")

    def get_target_currency(self):
        return self.config.get("exchange", "target_currency")

    def get_exchange_threshold(self):
        return self.config.getfloat("exchange", "threshold")

    def get_exchange_min_threshold(self):
        return self.config.getfloat("exchange", "min_threshold")

    def get_exchange_url_telegram(self):
        return self.config.get("telegram", "url_telegram")
