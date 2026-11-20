"""Experimental G3 config entry lifecycle."""
from homeassistant.exceptions import ConfigEntryNotReady
from .daikin_g3.community import CommunityAdapter
from .daikin_g3.media import Media
from .daikin_g3.album import Album
from .daikin_g3.notifications import Notifications
from .daikin_g3.ha_native import native_bridge

async def async_setup_entry(hass, entry):
    adapter=await hass.async_add_executor_job(CommunityAdapter,entry.data["url"],entry.data.get("password"))
    try:
        await adapter.info()
        await adapter.capabilities()
    except Exception as exc:
        raise ConfigEntryNotReady("G3 connection failed") from exc
    media=Media(adapter)
    entry.runtime_data={"adapter":adapter,"media":media,"album":Album(media),"notifications":Notifications(media),"bridge":native_bridge(hass)}
    return True

async def async_unload_entry(hass, entry):
    return True
