"""Deterministic tests for the bundled Doubao Search CLI."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("doubao_search.py")
SPEC = importlib.util.spec_from_file_location("doubao_search", MODULE_PATH)
assert SPEC and SPEC.loader
doubao = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doubao)


class FakeResponse:
    def __init__(self, data: dict):
        self.body = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.body


class PayloadTests(unittest.TestCase):
    def test_web_default_count_is_ten(self):
        args = doubao.make_parser().parse_args(["query"])
        self.assertEqual(doubao.build_payload(args)["Count"], 10)

    def test_image_default_count_is_five(self):
        args = doubao.make_parser().parse_args(["query", "--search-type", "image"])
        self.assertEqual(doubao.build_payload(args)["Count"], 5)

    def test_image_rejects_more_than_five(self):
        args = doubao.make_parser().parse_args(
            ["query", "--search-type", "image", "--count", "6"]
        )
        with self.assertRaises(doubao.SearchError):
            doubao.build_payload(args)

    def test_date_range_is_calendar_valid_and_ordered(self):
        with self.assertRaises(doubao.SearchError):
            doubao.validate_time_range("2026-02-30..2026-03-01")
        with self.assertRaises(doubao.SearchError):
            doubao.validate_time_range("2026-03-02..2026-03-01")


class CredentialTests(unittest.TestCase):
    def test_key_is_saved_atomically_to_requested_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / ".env"
            doubao.save_local_key("test-only-key", path)
            values = doubao.read_env_file(path)
            self.assertEqual(values["DOUBAO_SEARCH_API_KEY"], "test-only-key")
            self.assertFalse(path.with_name(".env.tmp").exists())

    def test_rate_limit_is_not_a_credential_error(self):
        self.assertFalse(doubao.credential_was_rejected("700429", "rate limited"))
        self.assertTrue(
            doubao.credential_was_rejected(
                "Unauthorized", "API key invalid", http_status=401
            )
        )


class RetryTests(unittest.TestCase):
    def test_http_429_retries_then_succeeds(self):
        error_body = {
            "ResponseMetadata": {
                "Error": {"Code": "700429", "Message": "rate limited"}
            }
        }
        rate_error = urllib.error.HTTPError(
            doubao.DEFAULT_ENDPOINT,
            429,
            "Too Many Requests",
            {"Retry-After": "0"},
            io.BytesIO(json.dumps(error_body).encode("utf-8")),
        )
        success = {"ResponseMetadata": {"RequestId": "ok"}, "Result": {}}
        with patch.object(
            doubao.urllib.request,
            "urlopen",
            side_effect=[rate_error, FakeResponse(success)],
        ) as urlopen_mock, patch.object(doubao.time, "sleep") as sleep_mock:
            result = doubao.call_api(
                doubao.validation_payload(),
                "test-only-key",
                max_retries=1,
            )
        self.assertEqual(result["ResponseMetadata"]["RequestId"], "ok")
        self.assertEqual(urlopen_mock.call_count, 2)
        sleep_mock.assert_called_once_with(0.0)


if __name__ == "__main__":
    unittest.main()
