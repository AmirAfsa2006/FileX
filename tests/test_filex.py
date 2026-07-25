"""Focused regression tests for FileX configuration and secure links."""

from __future__ import annotations

import asyncio
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Pyrofork's synchronous compatibility layer expects an import-time event loop
# on newer Python versions. Production supports Python 3.10+, where the service
# process supplies its normal loop through Client.run().
asyncio.set_event_loop(asyncio.new_event_loop())

import config
from helper_func import decode, encode, get_message_id, get_payload_ids


class EncodingTests(unittest.TestCase):
    def test_urlsafe_base64_round_trip_without_padding(self) -> None:
        payload = "get-123456789-987654321"
        encoded = asyncio.run(encode(payload))

        self.assertNotIn("=", encoded)
        self.assertEqual(asyncio.run(decode(encoded)), payload)

    def test_legacy_padded_payload_is_accepted(self) -> None:
        encoded = asyncio.run(encode("get-42"))
        self.assertEqual(asyncio.run(decode(encoded + "===")), "get-42")


class PayloadTests(unittest.TestCase):
    CHANNEL_ID = -123

    def test_single_payload(self) -> None:
        self.assertEqual(get_payload_ids("get-861", self.CHANNEL_ID), [7])

    def test_ascending_and_descending_batches(self) -> None:
        self.assertEqual(
            get_payload_ids("get-246-615", self.CHANNEL_ID),
            [2, 3, 4, 5],
        )
        self.assertEqual(
            get_payload_ids("get-615-246", self.CHANNEL_ID),
            [5, 4, 3, 2],
        )

    def test_payload_for_another_channel_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            get_payload_ids("get-247", self.CHANNEL_ID)

    def test_malformed_payload_is_rejected(self) -> None:
        for payload in ("", "set-123", "get", "get-1-2-3", "get-not-a-number"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                get_payload_ids(payload, self.CHANNEL_ID)


class MessageIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SimpleNamespace(
            db_channel=SimpleNamespace(id=-1001234567890, username="FileXStore")
        )

    def test_private_channel_post_link(self) -> None:
        message = SimpleNamespace(
            forward_from_chat=None,
            forward_from_message_id=None,
            forward_origin=None,
            forward_sender_name=None,
            text="https://t.me/c/1234567890/77",
        )
        self.assertEqual(
            asyncio.run(get_message_id(self.client, message)),
            77,
        )

    def test_public_channel_post_link_is_case_insensitive(self) -> None:
        message = SimpleNamespace(
            forward_from_chat=None,
            forward_from_message_id=None,
            forward_origin=None,
            forward_sender_name=None,
            text="https://telegram.me/filexstore/88?single",
        )
        self.assertEqual(
            asyncio.run(get_message_id(self.client, message)),
            88,
        )

    def test_link_from_another_channel_is_rejected(self) -> None:
        message = SimpleNamespace(
            forward_from_chat=None,
            forward_from_message_id=None,
            forward_origin=None,
            forward_sender_name=None,
            text="https://t.me/c/999/77",
        )
        self.assertEqual(asyncio.run(get_message_id(self.client, message)), 0)

    def test_pyrofork_forward_origin(self) -> None:
        message = SimpleNamespace(
            forward_from_chat=None,
            forward_from_message_id=None,
            forward_origin=SimpleNamespace(
                chat=SimpleNamespace(id=-1001234567890),
                message_id=91,
            ),
            forward_sender_name=None,
            text=None,
        )
        self.assertEqual(asyncio.run(get_message_id(self.client, message)), 91)


class ConfigurationTests(unittest.TestCase):
    CONFIG_KEYS = {
        "API_ID",
        "APP_ID",
        "API_HASH",
        "BOT_TOKEN",
        "TG_BOT_TOKEN",
        "OWNER_ID",
        "CHANNEL_ID",
        "DATABASE_URL",
        "DB_URI",
        "ADMINS",
        "FORCE_SUB_CHANNEL",
        "JOIN_REQUEST_ENABLED",
        "JOIN_REQUEST_ENABLE",
        "PROTECT_CONTENT",
        "DISABLE_CHANNEL_BUTTON",
        "AUTO_DELETE_TIME",
    }

    def _reload_config(self, values: dict[str, str]):
        environment = {key: value for key, value in os.environ.items() if key not in self.CONFIG_KEYS}
        environment.update(values)
        with patch.dict(os.environ, environment, clear=True):
            return importlib.reload(config)

    def tearDown(self) -> None:
        importlib.reload(config)

    def test_legacy_aliases_and_typed_values(self) -> None:
        loaded = self._reload_config(
            {
                "APP_ID": "12345",
                "API_HASH": "hash",
                "TG_BOT_TOKEN": "token",
                "OWNER_ID": "99",
                "CHANNEL_ID": "-10077",
                "DB_URI": "mongodb://localhost/filex",
                "ADMINS": "1, 2",
                "PROTECT_CONTENT": "yes",
                "AUTO_DELETE_TIME": "-20",
            }
        )

        self.assertEqual(loaded.API_ID, 12345)
        self.assertEqual(loaded.BOT_TOKEN, "token")
        self.assertEqual(loaded.DATABASE_URL, "mongodb://localhost/filex")
        self.assertEqual(loaded.ADMINS, [1, 2, 99])
        self.assertTrue(loaded.PROTECT_CONTENT)
        self.assertEqual(loaded.AUTO_DELETE_TIME, 0)
        loaded.validate_required_config()

    def test_missing_required_values_raise_clear_error(self) -> None:
        loaded = self._reload_config({})
        with self.assertRaisesRegex(RuntimeError, "API_ID.*API_HASH.*BOT_TOKEN"):
            loaded.validate_required_config()

    def test_invalid_boolean_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "PROTECT_CONTENT"):
            self._reload_config({"PROTECT_CONTENT": "sometimes"})


if __name__ == "__main__":
    unittest.main()