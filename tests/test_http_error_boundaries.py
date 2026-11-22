"""社区 G3 HTTP 错误边界测试：只识别明确 JSON busy，不重发写操作。

使用内存 HTTPError，属于协议模拟测试，不代表实机验证。
"""
import io
import unittest
from email.message import Message
from urllib.error import HTTPError

from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import CommandError


class FakeOpener:
    def __init__(self, payload, content_type="application/json", status=503):
        self.payload = payload
        self.content_type = content_type
        self.status = status
        self.calls = 0

    def open(self, request, timeout=None):
        self.calls += 1
        headers = Message()
        headers["Content-Type"] = self.content_type
        raise HTTPError(request.full_url, self.status, "mock overload",
                        headers, io.BytesIO(self.payload))


class TestHttpErrorBoundaries(unittest.TestCase):
    def setUp(self):
        self.adapter = CommunityAdapter("http://127.0.0.1:12345", "test")

    def check_error(self, payload, content_type, expected_busy):
        fake = FakeOpener(payload, content_type)
        self.adapter.opener = fake
        if expected_busy:
            with self.assertRaises(CommandError) as caught:
                self.adapter._request("/api/v1/command", b"request")
            self.assertEqual(caught.exception.code, "busy")
        else:
            with self.assertRaises(HTTPError) as caught:
                self.adapter._request("/api/v1/command", b"request")
            self.assertEqual(caught.exception.code, 503)
        self.assertEqual(fake.calls, 1)

    def test_exact_json_busy(self):
        self.check_error(b'{"code":"busy"}', "application/json", True)

    def test_nonbusy_json_remains_http_error(self):
        self.check_error(b'{"code":"unauthorized"}', "application/json", False)

    def test_malformed_json_remains_http_error(self):
        self.check_error(b'{"code":', "application/json", False)

    def test_wrong_content_type_never_downgrades(self):
        self.check_error(b'{"code":"busy"}', "text/plain", False)

    def test_oversized_json_error_remains_http_error(self):
        self.check_error(b'{"code":"busy"}' + b" " * 4097,
                         "application/json", False)

    def test_json_array_does_not_count_as_busy(self):
        self.check_error(b'[{"code":"busy"}]', "application/json", False)
