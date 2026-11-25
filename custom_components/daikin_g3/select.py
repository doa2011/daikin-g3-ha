from homeassistant.components.select import SelectEntity
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlbumSource(entry.runtime_data["album_controller"])])
class AlbumSource(AlbumEntity, SelectEntity):
    def __init__(self, c):
        self.init_album(c, "g3_album_source", "相册来源")
    @property
    def options(self):
        return self.controller.directories
    @property
    def current_option(self):
        return self.player.settings["directory"]
    async def async_select_option(self, option):
        await self.controller.select(option)
