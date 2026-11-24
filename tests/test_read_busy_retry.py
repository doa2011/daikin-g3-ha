"""Bounded retry tests; simulated transport, not hardware."""
import unittest
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError
from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import CommandError, ProtocolError


class TestReadBusyRetry(unittest.IsolatedAsyncioTestCase):
    async def test_recovers_on_third_attempt(self):
        adapter = CommunityAdapter("127.0.0.1")
        adapter._get = AsyncMock(side_effect=[CommandError("busy"), CommandError("busy"), {"actions": ["status.get"]}])
        with patch("daikin_g3.community.asyncio.sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(await adapter.capabilities(), frozenset({"status.get"}))
        self.assertEqual(adapter._get.await_count, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_persistent_busy_is_bounded(self):
        adapter = CommunityAdapter("127.0.0.1")
        adapter._get = AsyncMock(side_effect=CommandError("busy"))
        with patch("daikin_g3.community.asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaises(CommandError):
                await adapter.info()
        self.assertEqual(adapter._get.await_count, 3)

    async def test_other_errors_are_not_retried(self):
        for error in (CommandError("unsupported"), ProtocolError("bad encoding"), HTTPError("http://127.0.0.1", 401, "", {}, None)):
            adapter = CommunityAdapter("127.0.0.1")
            adapter._get = AsyncMock(side_effect=error)
            with self.assertRaises(type(error)):
                await adapter.status()
            self.assertEqual(adapter._get.await_count, 1)
