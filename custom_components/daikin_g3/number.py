from homeassistant.components.number import NumberEntity, NumberMode
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data["album_controller"]
    async_add_entities([AlbumNumber(c, "seconds"), AlbumNumber(c, "brightness")])
class AlbumNumber(AlbumEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    def __init__(self, c, key):
        self.key = key
        interval = key == "seconds"
        self.init_album(c, "g3_album_interval" if interval else "g3_album_brightness", "照片切换间隔" if interval else "相册亮度")
        self._attr_native_max_value = 3600 if interval else 100
        self._attr_native_unit_of_measurement = "s" if interval else "%"
    @property
    def native_value(self):
        return self.player.settings[self.key]
    async def async_set_native_value(self, value):
        self.controller.set_setting(self.key, int(value))
