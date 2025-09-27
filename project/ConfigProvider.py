import configparser
import os

global_config = configparser.ConfigParser(interpolation=None)
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
global_config.read(config_path)


class ConfigProvider:
    def __init__(self) -> None:
        self.config = global_config

    def get_exchange_url(self) -> str:
        """Формирует полный URL для запроса к ExchangeRate.host"""
        url_base = self.config.get('exchange', 'url_base')
        base_currency = self.get_base_currency()
        target_currency = self.get_target_currency()
        return f"{url_base}?base={base_currency}&symbols={target_currency}"

    def get_base_currency(self) -> str:
        return self.config.get('exchange', 'base_currency')

    def get_target_currency(self) -> str:
        return self.config.get('exchange', 'target_currency')

    def get_exchange_threshold(self) -> float:
        return self.config.getfloat('exchange', 'threshold')

    def get_exchange_min_threshold(self) -> float:
        return self.config.getfloat('exchange', 'min_threshold')

    def get_exchange_url_telegram(self) -> str:
        return self.config.get('telegram', 'url_telegram')

