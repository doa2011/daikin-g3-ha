"""Exercise actual HA service registry with a simulated G3 transport."""
import asyncio
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import selector
from homeassistant.util.yaml import load_yaml
from pathlib import Path
from custom_components.daikin_g3 import async_setup_entry, async_unload_entry
from custom_components.daikin_g3.services import SERVICES

async def main():
    hass=HomeAssistant(str(Path("dist").resolve()))
    entry=ConfigEntry(version=1,minor_version=1,domain="daikin_g3",title="G3 test",data={"url":"http://127.0.0.1"},source="user",options={},unique_id=None,discovery_keys={})
    adapter=AsyncMock()
    try:
        with patch("custom_components.daikin_g3.CommunityAdapter",return_value=adapter):
            assert await async_setup_entry(hass,entry)
        for name in SERVICES:
            assert hass.services.has_service("daikin_g3",name)
        descriptions=load_yaml(Path("dist/custom_components/daikin_g3/services.yaml"))
        for service in descriptions.values():
            for field in service["fields"].values():
                selector.selector(field["selector"])
        with patch("custom_components.daikin_g3.services.dispatch",new_callable=AsyncMock) as dispatch:
            # The registry lookup needs a config entry manager; substitute only this boundary.
            from types import SimpleNamespace
            with patch.object(hass,"config_entries",SimpleNamespace(async_get_entry=lambda ident: entry if ident==entry.entry_id else None)):
                await hass.services.async_call("daikin_g3","show_message",{"entry_id":entry.entry_id,"text":"test"},blocking=True)
            dispatch.assert_awaited_once()
        assert await async_unload_entry(hass,entry)
        assert not any(hass.services.has_service("daikin_g3",n) for n in SERVICES)
    finally:
        await hass.async_stop(force=True)

if __name__=="__main__":
    asyncio.run(main())
