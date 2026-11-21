import asyncio
import urllib.request
import urllib.parse
from .auth import auth_headers
from .protocol import encode_command, decode_object, decode_result, ProtocolError

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
        with self.opener.open(request, timeout=self.timeout) as response:
            if response.headers.get_content_type() != "application/msgpack":
                raise ProtocolError("unexpected response encoding")
            data = response.read(1048577)
            if len(data) > 1048576:
                raise ProtocolError("response too large")
            return data

    async def _get(self, path):
        return decode_object(await asyncio.to_thread(self._request, path))

    async def info(self):
        return await self._get("/api/v1/info")

    async def status(self):
        return await self._get("/api/v1/status")

    async def capabilities(self):
        data = await self._get("/api/v1/capabilities")
        # GET /api/v1/capabilities is a plain map on v1.0.0; the
        # capabilities.get command instead returns an envelope with data.actions.
        # Accept both explicitly, without guessing from unrelated nested keys.
        if "actions" in data:
            actions = data["actions"]
        elif isinstance(data.get("data"), dict):
            actions = data["data"].get("actions")
        else:
            actions = None
        if not isinstance(actions, list) or not all(isinstance(x, str) and x for x in actions):
            raise ProtocolError("unsupported actions format")
        return frozenset(actions)

    async def call(self, action, params):
        request_id, body = encode_command(action, params)
        result = await asyncio.to_thread(self._request, "/api/v1/command", body)
        return decode_result(result, request_id)
