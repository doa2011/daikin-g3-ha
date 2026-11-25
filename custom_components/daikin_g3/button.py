from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data["album_controller"]
    async_add_entities([AlbumButton(c, 1), AlbumButton(c, -1)])
class AlbumButton(AlbumEntity, ButtonEntity):
    def __init__(self, c, step):
        self.step = step
        self.init_album(c, "g3_album_next" if step == 1 else "g3_album_previous", "下一张照片" if step == 1 else "上一张照片")
    @property
    def available(self):
        return self.player.running
    async def async_press(self):
        try:
            self.player.navigate(self.step)
        except RuntimeError as exc:
            raise HomeAssistantError(str(exc)) from exc
