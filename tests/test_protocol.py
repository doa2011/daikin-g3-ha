import unittest
import msgpack
from daikin_g3.protocol import encode_command, decode_result, decode_object, ProtocolError, CommandError
from daikin_g3.auth import auth_headers
from daikin_g3.community import CommunityAdapter

class TestProtocol(unittest.TestCase):
    def test_command(self):
        rid, body = encode_command("status.get", {}, "abc")
        self.assertEqual(msgpack.unpackb(body,raw=False), {"request_id":"abc","action":"status.get","params":{}})
        self.assertEqual(rid,"abc")
    def test_response(self):
        data = msgpack.packb({"request_id":"abc","code":"accepted","data":{}})
        self.assertEqual(decode_result(data,"abc")["code"],"accepted")
        with self.assertRaises(ProtocolError): decode_result(data,"wrong")
    def test_busy(self):
        with self.assertRaises(CommandError):
            decode_result(msgpack.packb({"request_id":"abc","code":"busy"}),"abc")
    def test_auth(self):
        self.assertEqual(auth_headers("test"),{"Authorization":"Basic YWRtaW46dGVzdA=="})
        self.assertEqual(auth_headers(None),{})
    def test_origin(self):
        with self.assertRaises(ValueError): CommunityAdapter("http://admin:secret@host")

class TestCapabilityEnvelope(unittest.IsolatedAsyncioTestCase):
    async def test_plain_capability_map(self):
        adapter = CommunityAdapter("http://127.0.0.1")
        async def fake_get(path):
            self.assertEqual(path, "/api/v1/capabilities")
            return {"actions": ["status.get", "screen.page.get"]}
        adapter._get = fake_get
        self.assertEqual(await adapter.capabilities(), frozenset({"status.get", "screen.page.get"}))

    async def test_command_style_envelope(self):
        adapter = CommunityAdapter("http://127.0.0.1")
        async def fake_get(path):
            return {"code": "ok", "data": {"actions": ["status.get"]}}
        adapter._get = fake_get
        self.assertEqual(await adapter.capabilities(), frozenset({"status.get"}))

    async def test_invalid_action_rejected(self):
        adapter = CommunityAdapter("http://127.0.0.1")
        async def fake_get(path):
            return {"data": {"actions": ["status.get", None]}}
        adapter._get = fake_get
        with self.assertRaises(ProtocolError):
            await adapter.capabilities()

class TestMalformedMessagePack(unittest.TestCase):
    """Regression cases for malformed v1.0.0 binary HTTP responses."""

    def test_truncated_map(self):
        with self.assertRaisesRegex(ProtocolError, "invalid MessagePack"):
            decode_object(b"\\x81\\xa6broken")

    def test_extra_trailing_object(self):
        body = msgpack.packb({"code": "ok"}, use_bin_type=True) + msgpack.packb(42)
        with self.assertRaisesRegex(ProtocolError, "invalid MessagePack"):
            decode_object(body)

    def test_reserved_invalid_byte(self):
        with self.assertRaisesRegex(ProtocolError, "invalid MessagePack"):
            decode_object(b"\\xc1")

    def test_non_map_root(self):
        with self.assertRaisesRegex(ProtocolError, "expected map"):
            decode_object(msgpack.packb(["not", "a", "map"]))

    def test_valid_binary_data_preserved(self):
        payload = {"request_id": "a", "code": "ok", "data": {"jpeg": b"\\xff\\xd8"}}
        self.assertEqual(decode_result(msgpack.packb(payload, use_bin_type=True), "a"), payload)

    def test_wrong_request_id_not_masked(self):
        payload = {"request_id": "a", "code": "ok", "data": {}}
        with self.assertRaisesRegex(ProtocolError, "request ID mismatch"):
            decode_result(msgpack.packb(payload, use_bin_type=True), "b")
