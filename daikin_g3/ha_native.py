"""Native Home Assistant readers, imported lazily for standalone use."""
from .ha_bridge import HABridge

def native_bridge(hass):
    from homeassistant.components import camera
    from homeassistant.exceptions import HomeAssistantError

    async def read_state(entity_id):
        state=hass.states.get(entity_id)
        return None if state is None else {"state":state.state,"attributes":dict(state.attributes)}

    async def read_camera(entity_id):
        image=await camera.async_get_image(hass,entity_id,timeout=10)
        if image is None or not image.content:
            raise HomeAssistantError("Camera returned no image")
        return image.content

    return HABridge(read_state,read_camera)
