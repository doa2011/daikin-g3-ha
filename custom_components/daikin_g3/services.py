import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from .daikin_g3.ha_services import dispatch

DOMAIN="daikin_g3"
SERVICES=("show_message","show_camera","show_dashboard","dismiss","start_album","stop_album")
ID=vol.All(vol.Coerce(int),vol.Range(min=1,max=0xffffffff))
BASE={vol.Required("entry_id"):cv.string}
DISPLAY={vol.Optional("seconds"):vol.All(vol.Coerce(int),vol.Range(min=1,max=3600)),vol.Optional("brightness"):vol.All(vol.Coerce(int),vol.Range(min=1,max=100)),vol.Optional("wake"):cv.boolean}
NOTICE={vol.Optional("notice_id"):ID,vol.Optional("title"):cv.string}
SCHEMAS={
    "show_message":vol.Schema({**BASE,**DISPLAY,**NOTICE,vol.Required("text"):cv.string}),
    "show_camera":vol.Schema({**BASE,**DISPLAY,**NOTICE,vol.Required("camera"):cv.entity_id}),
    "show_dashboard":vol.Schema({**BASE,**DISPLAY,vol.Optional("title"):cv.string,vol.Required("entities"):vol.All(cv.ensure_list,[cv.entity_id],vol.Length(min=1,max=8))}),
    "dismiss":vol.Schema({**BASE,vol.Required("notice_id"):ID}),
    "start_album":vol.Schema({**BASE,**DISPLAY,vol.Required("directory"):cv.string,vol.Optional("shuffle",default=False):cv.boolean}),
    "stop_album":vol.Schema(dict(BASE)),
}

def register(hass):
    async def handle(call):
        entry=hass.config_entries.async_get_entry(call.data["entry_id"])
        if entry is None or entry.domain!=DOMAIN or entry.entry_id not in hass.data.get(DOMAIN,{}):
            raise HomeAssistantError("G3 entry not loaded")
        runtime=hass.data[DOMAIN][entry.entry_id]
        try:
            async with runtime["service_lock"]:
                await dispatch(runtime,call.service,call.data)
        except Exception as exc:
            raise HomeAssistantError("G3 service failed") from exc
    for name in SERVICES:
        hass.services.async_register(DOMAIN,name,handle,schema=SCHEMAS[name])

def unregister(hass):
    for name in SERVICES:
        hass.services.async_remove(DOMAIN,name)
