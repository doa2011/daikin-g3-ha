"""Experimental G3 config entry lifecycle."""
import asyncio
from homeassistant.exceptions import ConfigEntryNotReady
from .daikin_g3.community import CommunityAdapter
from .daikin_g3.media import Media
from .daikin_g3.album import Album
from .daikin_g3.media_queue import MediaTaskQueue
from .daikin_g3.notifications import Notifications
from .daikin_g3.ha_native import native_bridge
from .services import DOMAIN, register, unregister

async def async_setup_entry(hass, entry):
    adapter=await hass.async_add_executor_job(CommunityAdapter,entry.data["url"],entry.data.get("password"))
    try:
        await adapter.info()
        await adapter.capabilities()
    except Exception as exc:
        raise ConfigEntryNotReady("G3 connection failed") from exc
    media=Media(adapter)
    album=Album(media)
    entry.runtime_data={"adapter":adapter,"media":media,"album":album,"media_queue":MediaTaskQueue(album),"notifications":Notifications(media),"bridge":native_bridge(hass),"service_lock":asyncio.Lock()}
    entries=hass.data.setdefault(DOMAIN,{})
    if not entries:
        register(hass)
    entries[entry.entry_id]=entry.runtime_data
    return True

async def async_unload_entry(hass, entry):
    entries=hass.data.get(DOMAIN,{})
    runtime=entries.pop(entry.entry_id,None)
    if runtime:
        await runtime["media_queue"].close()
    if not entries:
        unregister(hass)
    return True
