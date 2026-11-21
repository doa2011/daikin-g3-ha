"""Service dispatch independent of HA runtime for unit testing."""
import secrets

def new_id():
    return secrets.randbelow(0x7fffffff)+1

async def dispatch(runtime, service, data):
    settings={k:data[k] for k in ("seconds","brightness","wake") if k in data}
    if service=="show_message":
        return await runtime["notifications"].send(data.get("notice_id") or new_id(),title=data.get("title",""),text=data["text"],**settings)
    if service=="show_camera":
        return await runtime["bridge"].snapshot(runtime["notifications"],data["camera"],data.get("notice_id") or new_id(),new_id(),title=data.get("title",""),**settings)
    if service=="show_dashboard":
        return await runtime["bridge"].dashboard(runtime["album"],data.get("title","Dashboard"),data["entities"],**settings)
    if service=="dismiss":
        return await runtime["notifications"].dismiss(data["notice_id"])
    raise ValueError("unknown G3 service")
