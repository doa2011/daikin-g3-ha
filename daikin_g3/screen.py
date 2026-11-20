"""Remote paging using the community G3 service contract."""
from .protocol import ProtocolError

class Screen:
    def __init__(self, adapter):
        self.adapter = adapter

    async def state(self):
        if "screen.page.get" not in await self.adapter.capabilities():
            raise ProtocolError("paging query unsupported")
        return (await self.adapter.call("screen.page.get", {}))["data"]

    async def _set(self, params):
        if "screen.page.set" not in await self.adapter.capabilities():
            raise ProtocolError("paging unsupported")
        state = await self.state()
        if state.get("supported") is not True or state.get("available") is not True:
            raise ProtocolError("screen unavailable")
        return await self.adapter.call("screen.page.set", params)

    async def next(self):
        return await self._set({"direction":"next"})

    async def previous(self):
        return await self._set({"direction":"previous"})

    async def goto(self, page):
        if type(page) is not int or not 1 <= page <= 8:
            raise ValueError("page must be an integer from 1 to 8")
        return await self._set({"page":page})
