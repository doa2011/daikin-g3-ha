"""Volatile external widget data, independent of Home Assistant."""
import math
from .protocol import ProtocolError

def payload(component_id, values=(), text="", ttl=60):
    if type(component_id) is not int or not 1 <= component_id <= 65535:
        raise ValueError("invalid component ID")
    if type(ttl) is not int or not 1 <= ttl <= 86400:
        raise ValueError("invalid TTL")
    if not isinstance(text,str) or "\x00" in text or len(text.encode("utf-8")) > 192:
        raise ValueError("invalid text")
    if not isinstance(values,(list,tuple)) or len(values)>64:
        raise ValueError("invalid values")
    for value in values:
        if type(value) not in (int,float) or abs(value)>1e9 or not math.isfinite(value):
            raise ValueError("invalid numeric value")
    return {"id":component_id,"values":list(values),"text":text,"ttl":ttl}

class ExternalData:
    def __init__(self, adapter):
        self.adapter = adapter

    async def push(self, component_id, values=(), text="", ttl=60):
        params = payload(component_id,values,text,ttl)
        if "screen.data.push" not in await self.adapter.capabilities():
            raise ProtocolError("external data unsupported")
        return await self.adapter.call("screen.data.push",params)
