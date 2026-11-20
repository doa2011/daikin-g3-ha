"""HA integration boundary; caller supplies authenticated camera/state readers."""
import re
from .dashboard import Tile, show_dashboard

def entity_id(value, domain=None):
    if not isinstance(value,str) or not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+",value):
        raise ValueError("invalid entity ID")
    if domain and value.split(".")[0]!=domain:
        raise ValueError("invalid entity domain")
    return value

class HABridge:
    def __init__(self, read_state, read_camera):
        self.read_state=read_state
        self.read_camera=read_camera

    async def snapshot(self, notifications, camera, notice_id, image_id, **settings):
        data=await self.read_camera(entity_id(camera,"camera"))
        if not isinstance(data,bytes) or not data or len(data)>16*1024*1024:
            raise ValueError("invalid camera image")
        return await notifications.send(notice_id,source=data,image_id=image_id,**settings)

    async def tiles(self, entities):
        if not isinstance(entities,(list,tuple)) or not 1<=len(entities)<=8:
            raise ValueError("one to eight entities required")
        result=[]
        for eid in entities:
            state=await self.read_state(entity_id(eid))
            if state is None:
                result.append(Tile(eid,"unavailable"))
                continue
            attrs=state.get("attributes") or {}
            result.append(Tile(str(attrs.get("friendly_name") or eid)[:80],
                               str(state.get("state","unknown"))[:80],
                               str(attrs.get("unit_of_measurement") or "")[:80]))
        return result

    async def dashboard(self, album, title, entities, **settings):
        return await show_dashboard(album,title,await self.tiles(entities),**settings)
