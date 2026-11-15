"""Poll exchange rates and notify Telegram only when the displayed rate changes."""

import argparse
import configparser
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import logging
from pathlib import Path
import time

import requests

from ConfigProvider import ConfigProvider
from DataProvider import DataProvider


LAST_RATE_FILE = Path(__file__).with_name("last_rate.json")
PRECISION = Decimal("0.001")
logger = logging.getLogger(__name__)


def round_rate(value):
    try:
        rate = Decimal(str(value))
        if not rate.is_finite() or rate <= 0:
            raise ValueError("Курс должен быть положительным конечным числом")
        rounded = rate.quantize(PRECISION, rounding=ROUND_HALF_UP)
        if rounded == 0:
            raise ValueError("Курс слишком мал для точности 0.001")
        return rounded
    except InvalidOperation as exc:
        raise ValueError("Некорректный курс валюты") from exc


class RateBot:
    def __init__(self, config, dp, state_file=LAST_RATE_FILE):
        self.config = config
        self.dp = dp
        self.state_file = Path(state_file)

    def get_rate(self):
        try:
            response = requests.get(
                self.config.get_exchange_url(),
                params={
                    "base": self.config.get_base_currency(),
                    "symbols": self.config.get_target_currency(),
                },
                headers={"apikey": self.dp.get_api_key()},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or data.get("success") is False:
                raise ValueError("API отклонил запрос")
            if data.get("base", self.config.get_base_currency()) != self.config.get_base_currency():
                raise ValueError("API вернул другую базовую валюту")
            return round_rate(data["rates"][self.config.get_target_currency()])
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            # Do not log request URLs or response bodies: they may contain credentials.
            logger.error("Не удалось получить курс (%s)", type(exc).__name__)
            return None

    def send_telegram(self, msg):
        url = (
            f"{self.config.get_exchange_url_telegram()}"
            f"{self.dp.get_telegram_token()}/sendMessage"
        )
        try:
            response = requests.post(
                url,
                data={"chat_id": self.dp.get_telegram_chat_id(), "text": msg},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or data.get("ok") is not True:
                raise ValueError("Telegram не подтвердил отправку")
            return True
        except (requests.RequestException, ValueError) as exc:
            logger.error("Не удалось отправить уведомление (%s)", type(exc).__name__)
            return False

    def load_last_rate(self):
        try:
            with self.state_file.open() as stream:
                return round_rate(json.load(stream)["last_rate"])
        except FileNotFoundError:
            return None
        except (ValueError, KeyError, TypeError):
            logger.warning("Некорректное сохранённое значение курса; начинаем заново")
            return None

    def save_last_rate(self, rate):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".json.tmp")
        with temporary.open("w") as stream:
            json.dump({"last_rate": float(rate)}, stream)
        temporary.replace(self.state_file)

    def check_once(self):
        current_rate = self.get_rate()
        if current_rate is None:
            return False

        try:
            last_rate = self.load_last_rate()
            if current_rate == last_rate:
                logger.info("Курс не изменился: %.3f", current_rate)
                return True

            pair = f"{self.config.get_base_currency()}/{self.config.get_target_currency()}"
            if last_rate is None:
                msg = f"Первый запуск. {pair}\nТекущий курс: {current_rate:.3f}"
            else:
                difference = current_rate - last_rate
                trend = "📈 Курс вырос" if difference > 0 else "📉 Курс упал"
                msg = (
                    f"{trend} ({pair})\n\n"
                    f"📊 Прошлый курс: {last_rate:.3f}\n"
                    f"📊 Текущий курс: {current_rate:.3f}\n"
                    f"Δ Разница: {difference:.3f}"
                )

            if not self.send_telegram(msg):
                return False
            # A failed delivery must be retried on the next poll.
            self.save_last_rate(current_rate)
            logger.info("Уведомление отправлено: %s", msg)
            return True
        except OSError as exc:
            logger.error("Ошибка сохранения/чтения курса (%s)", type(exc).__name__)
            return False


def run_forever(bot, interval):
    if interval < 1:
        raise ValueError("Интервал проверки должен быть не меньше 1 секунды")
    while True:
        bot.check_once()
        time.sleep(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Проверить курс один раз и выйти")
    parser.add_argument("--state-file", type=Path, default=LAST_RATE_FILE,
                        help="Файл последнего отправленного курса")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = ConfigProvider()
        dp = DataProvider()
        interval = config.get_poll_interval_seconds()
        if not all((config.get_exchange_url(), config.get_base_currency(),
                    config.get_target_currency(), config.get_exchange_url_telegram())):
            raise ValueError("В config.ini не заданы валюты или URL")
        if not dp.get_api_key():
            raise ValueError("Задайте APILAYER_API_KEY или access_key в data.json")
        if not dp.get_telegram_token() or not dp.get_telegram_chat_id():
            raise ValueError("Задайте TELEGRAM_TOKEN и TELEGRAM_CHAT_ID или TELEGRAM в data.json")
    except (OSError, ValueError, configparser.Error) as exc:
        logger.error("Проверьте config.ini и настройки APILAYER_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (%s)",
                     type(exc).__name__)
        return 1

    bot = RateBot(config, dp, args.state_file)
    if args.once:
        return 0 if bot.check_once() else 1
    logger.info("Мониторинг запущен; пауза между проверками — %s сек.", interval)
    try:
        run_forever(bot, interval)
    except KeyboardInterrupt:
        logger.info("Мониторинг остановлен")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
