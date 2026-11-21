"""G3 display trace requests, independent of paging."""
import asyncio
from .protocol import ProtocolError

class Diagnostics:
    def __init__(self, adapter):
        self.adapter = adapter
        self.lock = asyncio.Lock()

    async def _request(self, action, params):
        actions = await self.adapter.capabilities()
        if not {action,"screen.diagnostics.get"} <= actions:
            raise ProtocolError("diagnostics unsupported")
        receipt = await self.adapter.call(action, params)
        rid = receipt.get("data",{}).get("request")
        if receipt.get("code") != "accepted" or type(rid) is not int or not 0 < rid <= 0xffffffff:
            raise ProtocolError("missing diagnostic request")
        async def poll():
            while True:
                state = (await self.adapter.call("screen.diagnostics.get",{}))["data"]
                if state.get("request") != rid:
                    raise ProtocolError("diagnostic request superseded")
                if state.get("timeout"):
                    raise ProtocolError("MCU diagnostic timeout")
                if not state.get("pending") and state.get("available") and state.get("reply_request") == rid:
                    if state.get("status") != 0:
                        raise ProtocolError("MCU diagnostic rejected")
                    return state
                await asyncio.sleep(.25)
        return await asyncio.wait_for(poll(),7)

    async def start(self, mode="current", page=None):
        if mode not in ("current","next","page") or (mode=="page" and (type(page) is not int or not 1<=page<=8)) or (mode!="page" and page is not None):
            raise ValueError("invalid capture mode/page")
        params = {"mode":mode}
        if page is not None:
            params["page"] = page
        async with self.lock:
            return await self._request("screen.diagnostics.start",params)

    async def stop(self):
        async with self.lock:
            return await self._request("screen.diagnostics.stop",{})

    async def read(self):
        async with self.lock:
            records = []
            generation = None
            stored = None
            for offset in range(0,96,8):
                state = await self._request("screen.diagnostics.read",{"offset":offset,"limit":8})
                if generation is None:
                    generation = state["generation"]
                    stored = state["stored"]
                    if type(stored) is not int or not 0<=stored<=96:
                        raise ProtocolError("invalid stored count")
                if state.get("generation") != generation or state.get("stored") != stored:
                    raise ProtocolError("capture changed during read")
                batch = state.get("records")
                if not isinstance(batch,list) or state.get("offset")!=offset or state.get("returned")!=len(batch) or len(batch)!=min(8,stored-offset):
                    raise ProtocolError("invalid trace batch")
                if any(r.get("index")!=offset+i for i,r in enumerate(batch)):
                    raise ProtocolError("invalid trace index")
                records.extend(batch)
                if len(records)==stored:
                    return {**state,"records":records}
            raise ProtocolError("incomplete trace")
