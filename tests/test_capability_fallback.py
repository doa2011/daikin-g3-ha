import unittest
from unittest.mock import AsyncMock
from urllib.error import HTTPError
from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import ProtocolError, CommandError


class TestCapabilityFallback(unittest.IsolatedAsyncioTestCase):
    async def test_missing_get_route(self):
        for status in (404, 405):
            adapter = CommunityAdapter("127.0.0.1")
            adapter._read_query = AsyncMock(side_effect=HTTPError("", status, "", {}, None))
            adapter.call = AsyncMock(return_value={"code": "ok", "data": {"actions": ["status.get"]}})
            self.assertEqual(await adapter.capabilities(), frozenset({"status.get"}))
            adapter.call.assert_awaited_once_with("capabilities.get", {})

    async def test_no_fallback_for_other_errors(self):
        for error in (HTTPError("", 401, "", {}, None), HTTPError("", 403, "", {}, None), HTTPError("", 503, "", {}, None), CommandError("busy"), ProtocolError("bad encoding")):
            adapter = CommunityAdapter("127.0.0.1")
            adapter._read_query = AsyncMock(side_effect=error)
            adapter.call = AsyncMock()
            with self.assertRaises(type(error)):
                await adapter.capabilities()
            adapter.call.assert_not_awaited()

    async def test_invalid_fallback_actions(self):
        adapter = CommunityAdapter("127.0.0.1")
        adapter._read_query = AsyncMock(side_effect=HTTPError("", 404, "", {}, None))
        adapter.call = AsyncMock(return_value={"code": "ok", "data": {"actions": "status.get"}})
        with self.assertRaises(ProtocolError):
            await adapter.capabilities()
