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
        base_url = base_url.strip()
        if "://" not in base_url:
            base_url = "http://" + base_url
        url = urllib.parse.urlsplit(base_url)
        if any(ch.isspace() for ch in base_url):
            raise ValueError("expected device origin")
        _ = url.port  # Validate explicit port before any network request.
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
            # Upstream v1.0.0 may return JSON busy while the normal API is
            # MessagePack. This is an error signal, never a protocol downgrade.
            if exc.headers.get_content_type() == "application/json":
                payload = exc.read(4097)
                if len(payload) <= 4096:
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
        return decode_object(await asyncio.to_thread(self._request, path))

    async def _read_query(self, path):
        # Retry only explicit busy responses on known read-only endpoints.
        for attempt in range(3):
            try:
                return await self._get(path)
            except CommandError as exc:
                if exc.code != "busy" or attempt == 2:
                    raise
                await asyncio.sleep(0.25 * (attempt + 1))

    async def info(self):
        return await self._read_query("/api/v1/info")

    async def status(self):
        return await self._read_query("/api/v1/status")

    async def capabilities(self):
        try:
            data = await self._read_query("/api/v1/capabilities")
        except urllib.error.HTTPError as exc:
            # Only an absent GET route permits the documented read-only command.
            # Never mask authentication, busy, or malformed responses.
            if exc.code not in (404, 405):
                raise
            data = await self.call("capabilities.get", {})
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
