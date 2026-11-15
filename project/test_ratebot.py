"""Functional checks for RateBot; HTTP calls never leave the test process."""

from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, mock_open, patch

import requests

from DataProvider import DataProvider
from exchange_rate import RateBot, main, round_rate, run_forever


class RoundingTests(unittest.TestCase):
    def test_rounds_to_three_places_using_half_up(self):
        for value, expected in [
            ("2.6784", "2.678"),
            ("2.6785", "2.679"),
            (2.7, "2.700"),
            (Decimal("2.9995"), "3.000"),
        ]:
            with self.subTest(value=value):
                actual = round_rate(value)
                self.assertIsInstance(actual, Decimal)
                self.assertEqual(str(actual), expected)

    def test_rejects_invalid_or_nonpositive_rates(self):
        for value in [None, "bad", "", 0, -1, "0.0004", "NaN", "Infinity", "-Infinity"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    round_rate(value)


class RateBotTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_file = Path(self.temporary_directory.name) / "last_rate.json"
        self.config = Mock()
        self.config.get_exchange_url.return_value = (
            "https://api.apilayer.com/exchangerates_data/latest"
        )
        self.config.get_base_currency.return_value = "USD"
        self.config.get_target_currency.return_value = "GEL"
        self.config.get_exchange_url_telegram.return_value = "https://api.telegram.org/bot"
        self.config.get_poll_interval_seconds.return_value = 60
        self.dp = Mock()
        self.dp.get_api_key.return_value = "test-api-key"
        self.dp.get_telegram_token.return_value = "test-token"
        self.dp.get_telegram_chat_id.return_value = "test-chat"
        self.bot = RateBot(self.config, self.dp, state_file=self.state_file)

    def write_previous_rate(self, rate):
        self.state_file.write_text(json.dumps({"last_rate": rate}), encoding="utf-8")

    def stub_cycle(self, rate, *, delivered=True):
        self.bot.get_rate = Mock(return_value=rate)
        self.bot.send_telegram = Mock(return_value=delivered)

    def test_first_rate_is_sent_with_three_places_and_saved(self):
        self.stub_cycle(Decimal("2.700"))
        self.assertTrue(self.bot.check_once())
        self.bot.send_telegram.assert_called_once()
        message = self.bot.send_telegram.call_args.args[0]
        self.assertIn("2.700", message)
        self.assertEqual(self.bot.load_last_rate(), Decimal("2.700"))

    def test_rise_is_sent_with_rounded_previous_current_and_difference(self):
        self.write_previous_rate(2.6784)
        self.stub_cycle(Decimal("2.679"))
        self.assertTrue(self.bot.check_once())
        message = self.bot.send_telegram.call_args.args[0]
        self.assertIn("вырос", message.lower())
        for displayed_number in ("2.678", "2.679", "0.001"):
            self.assertIn(displayed_number, message)
        self.assertEqual(self.bot.load_last_rate(), Decimal("2.679"))

    def test_fall_is_sent_with_negative_three_place_difference(self):
        self.write_previous_rate(2.701)
        self.stub_cycle(Decimal("2.700"))
        self.assertTrue(self.bot.check_once())
        message = self.bot.send_telegram.call_args.args[0]
        self.assertIn("упал", message.lower())
        for displayed_number in ("2.701", "2.700", "-0.001"):
            self.assertIn(displayed_number, message)
        self.assertEqual(self.bot.load_last_rate(), Decimal("2.700"))

    def test_same_rounded_rate_does_not_send_or_write_state(self):
        self.write_previous_rate(2.7004)
        previous_contents = self.state_file.read_bytes()
        self.stub_cycle(Decimal("2.700"))
        self.assertTrue(self.bot.check_once())
        self.bot.send_telegram.assert_not_called()
        self.assertEqual(self.state_file.read_bytes(), previous_contents)

    def test_failed_delivery_preserves_previous_rate_for_retry(self):
        self.write_previous_rate(2.678)
        previous_contents = self.state_file.read_bytes()
        self.stub_cycle(Decimal("2.679"), delivered=False)
        self.assertFalse(self.bot.check_once())
        self.assertEqual(self.state_file.read_bytes(), previous_contents)
        self.bot.send_telegram.return_value = True
        self.assertTrue(self.bot.check_once())
        self.assertEqual(self.bot.send_telegram.call_count, 2)
        self.assertEqual(self.bot.load_last_rate(), Decimal("2.679"))

    def test_failed_first_delivery_does_not_create_state(self):
        self.stub_cycle(Decimal("2.700"), delivered=False)
        self.assertFalse(self.bot.check_once())
        self.assertFalse(self.state_file.exists())

    def test_missing_rate_does_not_send_or_change_state(self):
        self.write_previous_rate(2.7)
        previous_contents = self.state_file.read_bytes()
        self.stub_cycle(None)
        self.assertFalse(self.bot.check_once())
        self.bot.send_telegram.assert_not_called()
        self.assertEqual(self.state_file.read_bytes(), previous_contents)

    def test_load_missing_state(self):
        self.assertIsNone(self.bot.load_last_rate())

    def test_load_invalid_state(self):
        for contents in ("not json", "{}", '{"last_rate": "NaN"}', '{"last_rate": -1}'):
            with self.subTest(contents=contents):
                self.state_file.write_text(contents, encoding="utf-8")
                self.assertIsNone(self.bot.load_last_rate())

    def test_save_then_reload_preserves_rounded_rate(self):
        self.bot.save_last_rate(Decimal("2.679"))
        restored = RateBot(self.config, self.dp, state_file=self.state_file)
        self.assertEqual(restored.load_last_rate(), Decimal("2.679"))

    @patch("exchange_rate.requests.get")
    def test_get_rate_uses_apilayer_parameters_and_authentication(self, get):
        get.return_value.json.return_value = {
            "success": True, "rates": {"GEL": 2.6785}
        }
        self.assertEqual(self.bot.get_rate(), Decimal("2.679"))
        get.assert_called_once_with(
            "https://api.apilayer.com/exchangerates_data/latest",
            params={"base": "USD", "symbols": "GEL"},
            headers={"apikey": "test-api-key"},
            timeout=10,
        )
        get.return_value.raise_for_status.assert_called_once()

    @patch("exchange_rate.requests.get")
    def test_get_rate_rejects_http_error(self, get):
        get.return_value.raise_for_status.side_effect = requests.HTTPError("HTTP 429")
        self.assertIsNone(self.bot.get_rate())

    @patch("exchange_rate.requests.get")
    def test_get_rate_handles_timeout(self, get):
        get.side_effect = requests.Timeout("timed out")
        self.assertIsNone(self.bot.get_rate())

    @patch("exchange_rate.requests.get")
    def test_get_rate_rejects_unsuccessful_payload_even_with_rates(self, get):
        get.return_value.json.return_value = {
            "success": False, "rates": {"GEL": 2.7}
        }
        self.assertIsNone(self.bot.get_rate())

    @patch("exchange_rate.requests.get")
    def test_get_rate_handles_invalid_json(self, get):
        get.return_value.json.side_effect = ValueError("invalid JSON")
        self.assertIsNone(self.bot.get_rate())

    @patch("exchange_rate.requests.get")
    def test_get_rate_rejects_missing_or_invalid_currency(self, get):
        for rates in ({}, {"EUR": 1.0}, {"GEL": "NaN"}, {"GEL": 0}):
            with self.subTest(rates=rates):
                get.return_value.json.return_value = {"success": True, "rates": rates}
                self.assertIsNone(self.bot.get_rate())

    @patch("exchange_rate.requests.post")
    def test_send_telegram_checks_delivery_result(self, post):
        post.return_value.json.return_value = {"ok": True}
        self.assertTrue(self.bot.send_telegram("Курс: 2.700"))
        post.assert_called_once_with(
            "https://api.telegram.org/bottest-token/sendMessage",
            data={"chat_id": "test-chat", "text": "Курс: 2.700"},
            timeout=10,
        )
        post.return_value.raise_for_status.assert_called_once()

    @patch("exchange_rate.requests.post")
    def test_send_telegram_rejects_http_error(self, post):
        post.return_value.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
        self.assertFalse(self.bot.send_telegram("Курс: 2.700"))

    @patch("exchange_rate.requests.post")
    def test_send_telegram_rejects_ok_false(self, post):
        post.return_value.json.return_value = {"ok": False}
        self.assertFalse(self.bot.send_telegram("Курс: 2.700"))

    @patch("exchange_rate.requests.post")
    def test_send_telegram_handles_timeout(self, post):
        post.side_effect = requests.Timeout("timed out")
        self.assertFalse(self.bot.send_telegram("Курс: 2.700"))

    @patch("exchange_rate.requests.post")
    def test_send_telegram_handles_invalid_json(self, post):
        post.return_value.json.side_effect = ValueError("invalid JSON")
        self.assertFalse(self.bot.send_telegram("Курс: 2.700"))


class MonitorTests(unittest.TestCase):
    @patch("exchange_rate.time.sleep", side_effect=[None, KeyboardInterrupt])
    def test_monitor_retries_after_failed_cycle_and_can_be_interrupted(self, sleep):
        bot = Mock()
        bot.check_once.side_effect = [False, True]
        with self.assertRaises(KeyboardInterrupt):
            run_forever(bot, 60)
        self.assertEqual(bot.check_once.call_count, 2)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(60)


class CredentialTests(unittest.TestCase):
    environment_values = {
        "APILAYER_API_KEY": "env-api",
        "TELEGRAM_TOKEN": "env-token",
        "TELEGRAM_CHAT_ID": "env-chat",
    }
    file_contents = json.dumps({
        "access_key": "file-api",
        "TELEGRAM": {"TOKEN": "file-token", "CHAT_ID": "file-chat"},
    })

    def credentials(self, provider):
        return (provider.get_api_key(), provider.get_telegram_token(),
                provider.get_telegram_chat_id())

    def test_environment_credentials_work_without_data_file(self):
        with patch.dict(os.environ, self.environment_values, clear=True), \
                patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(self.credentials(DataProvider()),
                             ("env-api", "env-token", "env-chat"))

    def test_environment_credentials_override_data_file(self):
        with patch.dict(os.environ, self.environment_values, clear=True), \
                patch("builtins.open", mock_open(read_data=self.file_contents)):
            self.assertEqual(self.credentials(DataProvider()),
                             ("env-api", "env-token", "env-chat"))

    def test_data_file_credentials_work_without_environment_values(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch("builtins.open", mock_open(read_data=self.file_contents)):
            self.assertEqual(self.credentials(DataProvider()),
                             ("file-api", "file-token", "file-chat"))

    @patch("exchange_rate.requests.post")
    @patch("exchange_rate.requests.get")
    def test_missing_credentials_fail_before_network_request(self, get, post):
        with patch.dict(os.environ, {}, clear=True), \
                patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(main(["--once"]), 1)
        get.assert_not_called()
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
