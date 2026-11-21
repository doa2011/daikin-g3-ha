"""Volatile external chart series."""
import math
from .external_data import payload
from .protocol import ProtocolError

def series_payload(component_id, series, ttl=60, *, additive=False):
    base = payload(component_id, ttl=ttl)
    if not isinstance(series,(list,tuple)) or not 1<=len(series)<=3:
        raise ValueError("one to three series required")
    result=[]
    units=set()
    for item in series:
        if not isinstance(item,dict) or set(item)!={"name","unit","values"}:
            raise ValueError("invalid series keys")
        name,unit,values=item["name"],item["unit"],item["values"]
        if not all(isinstance(s,str) and "\x00" not in s for s in (name,unit)):
            raise ValueError("invalid series label")
        if not isinstance(values,(list,tuple)) or not 1<=len(values)<=32:
            raise ValueError("one to 32 points required")
        for value in values:
            if value is None:
                continue
            if type(value) not in (int,float) or abs(value)>1e9 or not math.isfinite(value):
                raise ValueError("invalid chart value")
            if additive and value<0:
                raise ValueError("negative additive chart value")
        units.add(unit)
        result.append({"name":name,"unit":unit,"values":list(values)})
    if additive and len(units)!=1:
        raise ValueError("additive chart units must match")
    return {"id":base["id"],"ttl":base["ttl"],"series":result}

class Charts:
    def __init__(self, adapter):
        self.adapter=adapter

    async def push(self, component_id, series, ttl=60, *, additive=False):
        params=series_payload(component_id,series,ttl,additive=additive)
        if "screen.data.series" not in await self.adapter.capabilities():
            raise ProtocolError("external charts unsupported")
        return await self.adapter.call("screen.data.series",params)
