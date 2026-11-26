import asyncio
import urllib.request
import urllib.parse
import urllib.error
import json
from .auth import auth_headers
from .protocol import encode_command, decode_object, decode_result, ProtocolError, CommandError

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class CommunityAdapter:
    def __init__(self, base_url, password=None, timeout=10):
        url = urllib.parse.urlsplit(base_url)
        if url.scheme not in ("http","https") or not url.hostname or url.username or url.password or url.path not in ("","/") or url.query or url.fragment:
            raise ValueError("expected device origin")
        self.base_url = base_url.rstrip("/")
        self.headers = auth_headers(password)
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _request(self, path, body=None):
        headers = {**self.headers, "Accept":"application/msgpack"}
        if body is not None:
            headers["Content-Type"] = "application/msgpack"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers)
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            # Keep bounded response details for diagnostics. Never log request
            # headers or credentials, and never downgrade an HTTP error to
            # MessagePack. The exact JSON busy signal remains non-retryable.
            try:
                payload = exc.read(4097)
            except OSError:
                payload = b""
            headers = exc.headers
            content_type = headers.get_content_type() if headers else ""
            exc.g3_status = exc.code
            exc.g3_path = urllib.parse.urlsplit(exc.url).path
            exc.g3_content_type = content_type
            exc.g3_body = payload[:512].decode("utf-8", errors="replace")
            exc.g3_body_truncated = len(payload) > 512
            if content_type == "application/json" and len(payload) <= 4096:
                try:
                    error = json.loads(payload)
                except (ValueError, UnicodeDecodeError):
                    error = None
                if isinstance(error, dict) and error.get("code") == "busy":
                    raise CommandError("busy") from exc
            raise
        with response:
            if response.headers.get_content_type() != "application/msgpack":
                raise ProtocolError("unexpected response encoding")
            data = response.read(1048577)
            if len(data) > 1048576:
                raise ProtocolError("response too large")
            return data

    async def _get(self, path):
        try:
            return decode_object(await asyncio.to_thread(self._request, path))
        except urllib.error.HTTPError as exc:
            exc.g3_action = "GET " + path
            raise

    async def info(self):
        return await self._get("/api/v1/info")

    async def status(self):
        return await self._get("/api/v1/status")

    async def capabilities(self):
        # G3 firmware exposes capability discovery as the read-only
        # capabilities.get command. Do not use GET /api/v1/capabilities:
        # that route is not registered by the BRY88BBA15G HTTP server.
        result = await self.call("capabilities.get", {})
        data = result.get("data")
        if not isinstance(data, dict):
            raise ProtocolError("invalid capabilities response")
        actions = data.get("actions")
        if not isinstance(actions, list) or not all(isinstance(x, str) and x for x in actions):
            raise ProtocolError("unsupported actions format")
        return frozenset(actions)

    async def call(self, action, params):
        request_id, body = encode_command(action, params)
        try:
            result = await asyncio.to_thread(self._request, "/api/v1/command", body)
        except urllib.error.HTTPError as exc:
            exc.g3_action = action
            raise
        return decode_result(result, request_id)
