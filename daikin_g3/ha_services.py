"""Service dispatch independent of HA runtime for unit testing."""
import secrets

def new_id():
    return secrets.randbelow(0x7fffffff)+1

async def dispatch(runtime, service, data):
    settings={k:data[k] for k in ("seconds","brightness","wake") if k in data}
    queue=runtime.get("media_queue")
    if service=="start_album":
        return await queue.start_album(data["directory"],shuffle=data.get("shuffle",False),**settings)
    if service=="stop_album":
        return await queue.stop_album()
    if service in ("show_message","show_camera","show_dashboard") and queue is not None:
        if service == "show_dashboard" or getattr(queue, "native_album", False) is not True:
            await queue.foreground()
    if service=="show_message":
        return await runtime["notifications"].send(data.get("notice_id") or new_id(),title=data.get("title",""),text=data["text"],**settings)
    if service=="show_camera":
        return await runtime["bridge"].snapshot(runtime["notifications"],data["camera"],data.get("notice_id") or new_id(),new_id(),title=data.get("title",""),**settings)
    if service=="show_dashboard":
        return await runtime["bridge"].dashboard(runtime["album"],data.get("title","Dashboard"),data["entities"],**settings)
    if service=="dismiss":
        return await runtime["notifications"].dismiss(data["notice_id"])
    raise ValueError("unknown G3 service")
