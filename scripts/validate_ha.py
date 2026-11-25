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


async def validate_config_flow(hass):
    """Exercise the real HA ConfigFlow class without contacting hardware."""
    from custom_components.daikin_g3.config_flow import G3ConfigFlow

    def new_flow():
        flow = G3ConfigFlow()
        flow.hass = hass
        return flow

    # Minimal identity is sufficient; status must not be queried.
    adapter = AsyncMock()
    adapter.base_url = "http://127.0.0.1"
    adapter.info.return_value = {"model": "daikin"}
    adapter.status.return_value = {}
    adapter.capabilities.return_value = frozenset({"status.get"})
    with patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=adapter), \
         patch.object(G3ConfigFlow, "_async_abort_entries_match") as duplicate_check, \
         patch.object(G3ConfigFlow, "async_create_entry", return_value={"type": "create_entry"}) as create:
        result = await new_flow().async_step_user({"url": "http://127.0.0.1/", "password": "test"})
        assert result["type"] == "create_entry"
        adapter.info.assert_awaited_once()
        adapter.status.assert_not_awaited()
        adapter.capabilities.assert_awaited_once()
        duplicate_check.assert_called_once_with({"url": adapter.base_url})
        assert create.call_args.kwargs["data"]["url"] == adapter.base_url

    # Optional capabilities failure must not block onboarding.
    adapter.reset_mock()
    adapter.capabilities.side_effect = ConnectionError("capabilities unavailable")
    with patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=adapter), \
         patch.object(G3ConfigFlow, "_async_abort_entries_match"), \
         patch.object(G3ConfigFlow, "async_create_entry", return_value={"type": "create_entry"}):
        result = await new_flow().async_step_user({"url": "http://127.0.0.1"})
        assert result["type"] == "create_entry"
        adapter.status.assert_not_awaited()
        adapter.capabilities.assert_awaited_once()

    # Invalid device origin and network errors must remain recoverable forms.
    with patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, side_effect=ValueError("bad URL")), \
         patch.object(G3ConfigFlow, "async_show_form", side_effect=lambda **kw: kw):
        result = await new_flow().async_step_user({"url": "file:///tmp/g3"})
        assert result["errors"]["base"] == "invalid_url"

    failing_adapter = AsyncMock()
    failing_adapter.info.side_effect = ConnectionError("device offline")
    with patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=failing_adapter), \
         patch.object(G3ConfigFlow, "async_show_form", side_effect=lambda **kw: kw):
        result = await new_flow().async_step_user({"url": "http://127.0.0.1"})
        assert result["errors"]["base"] == "cannot_connect"
        failing_adapter.capabilities.assert_not_awaited()

async def main():
    hass=HomeAssistant(str(Path("dist").resolve()))
    await validate_config_flow(hass)
    entry=ConfigEntry(version=1,minor_version=1,domain="daikin_g3",title="G3 test",data={"url":"http://127.0.0.1"},source="user",options={},unique_id=None,discovery_keys={},subentries_data=[])
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
        # A second G3 must retain shared services after the first unloads.
        second=ConfigEntry(version=1,minor_version=1,domain="daikin_g3",title="G3 second",data={"url":"http://127.0.0.2"},source="user",options={},unique_id=None,discovery_keys={},subentries_data=[])
        with patch("custom_components.daikin_g3.CommunityAdapter",return_value=AsyncMock()):
            assert await async_setup_entry(hass,second)
        assert len(hass.data["daikin_g3"]) == 2
        assert await async_unload_entry(hass,entry)
        assert all(hass.services.has_service("daikin_g3",n) for n in SERVICES)
        with patch("custom_components.daikin_g3.services.dispatch",new_callable=AsyncMock) as dispatch:
            from types import SimpleNamespace
            with patch.object(hass,"config_entries",SimpleNamespace(async_get_entry=lambda ident: second if ident==second.entry_id else None)):
                await hass.services.async_call("daikin_g3","show_message",{"entry_id":second.entry_id,"text":"second device"},blocking=True)
            dispatch.assert_awaited_once()
        assert await async_unload_entry(hass,second)
        assert not any(hass.services.has_service("daikin_g3",n) for n in SERVICES)
    finally:
        await hass.async_stop(force=True)

if __name__=="__main__":
    asyncio.run(main())
