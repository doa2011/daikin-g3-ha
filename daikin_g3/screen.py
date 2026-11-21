"""Remote paging and MCU completion tracking."""
import asyncio
from .protocol import ProtocolError

class Screen:
    def __init__(self, adapter):
        self.adapter = adapter
        self._lock = asyncio.Lock()

    async def state(self):
        if "screen.page.get" not in await self.adapter.capabilities():
            raise ProtocolError("paging query unsupported")
        return await self._state()

    async def _state(self):
        return (await self.adapter.call("screen.page.get", {}))["data"]

    async def _set(self, params):
        if not {"screen.page.get","screen.page.set"} <= await self.adapter.capabilities():
            raise ProtocolError("paging unsupported")
        state = await self._state()
        if state.get("supported") is not True or state.get("available") is not True:
            raise ProtocolError("screen unavailable")
        if "page" in params and "enabled_mask" in state:
            if not state["enabled_mask"] & (1 << (params["page"]-1)):
                raise ProtocolError("page disabled")
        return await self.adapter.call("screen.page.set", params)

    async def wait(self, receipt, timeout=7, interval=0.25):
        request = receipt.get("data",{}).get("request")
        if receipt.get("code") != "accepted" or type(request) is not int or not 0 < request <= 0xffffffff:
            raise ProtocolError("missing MCU request ID")
        if timeout <= 0 or interval <= 0:
            raise ValueError("positive timeout and interval required")
        async def poll():
            while True:
                state = await self._state()
                if state.get("request") != request:
                    raise ProtocolError("MCU request superseded or reset")
                status = state.get("state")
                if status in ("invalid_page","mcu_busy","timeout"):
                    raise ProtocolError(status)
                if status == "complete" and state.get("available") is True and state.get("supported") is True:
                    return state
                if status not in ("pending","complete"):
                    raise ProtocolError("unknown MCU request state")
                await asyncio.sleep(interval)
        return await asyncio.wait_for(poll(), timeout)

    async def _execute(self, params, confirm):
        async with self._lock:
            receipt = await self._set(params)
            return await self.wait(receipt) if confirm else receipt

    async def next(self, *, confirm=False):
        return await self._execute({"direction":"next"}, confirm)

    async def previous(self, *, confirm=False):
        return await self._execute({"direction":"previous"}, confirm)

    async def goto(self, page, *, confirm=False):
        if type(page) is not int or not 1 <= page <= 8:
            raise ValueError("page must be an integer from 1 to 8")
        return await self._execute({"page":page}, confirm)
