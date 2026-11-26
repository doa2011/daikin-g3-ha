from homeassistant.components.image import ImageEntity
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AlbumImage(hass, entry.runtime_data["album_controller"])])
class AlbumImage(AlbumEntity, ImageEntity):
    def __init__(self, hass, c):
        ImageEntity.__init__(self, hass)
        self.init_album(c, "g3_album_current", "当前照片")
        self._attr_content_type = "image/jpeg"
    @property
    def image_last_updated(self):
        return self.player.updated
    @property
    def available(self):
        return self.player.current is not None
    async def async_image(self):
        return self.player.current
