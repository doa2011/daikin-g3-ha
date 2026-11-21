import unittest
import msgpack
from daikin_g3.protocol import encode_command, decode_result, ProtocolError, CommandError
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
