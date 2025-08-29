import configparser
import os

global_config = configparser.ConfigParser(interpolation=None)
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
global_config.read(config_path)

class ConfigProvider:
    def __init__(self) -> None:
        self.config = global_config

    def get_exchange_url(self):
        return self.config.get('exchange', 'usd_url')
    
    def get_exchange_threshold(self):
        return self.config.getfloat('exchange', 'threshold')