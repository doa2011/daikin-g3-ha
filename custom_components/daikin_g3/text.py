from homeassistant.components.text import TextEntity
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlbumDirectories(entry.runtime_data["album_controller"])])
class AlbumDirectories(AlbumEntity, TextEntity):
    _attr_native_max = 255
    def __init__(self, c):
        self.init_album(c, "g3_album_directories", "相册目录（分号分隔）")
    @property
    def native_value(self):
        return ";".join(self.controller.directories)
    async def async_set_value(self, value):
        await self.controller.set_directories(value)
