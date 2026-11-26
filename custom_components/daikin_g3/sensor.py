from homeassistant.components.sensor import SensorEntity
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data["album_controller"]
    async_add_entities([AlbumSensor(c, "count", "照片数量"), AlbumSensor(c, "status", "播放状态"), AlbumSensor(c, "last_error", "最近异常")])
class AlbumSensor(AlbumEntity, SensorEntity):
    def __init__(self, c, key, name):
        self.key = key
        self.init_album(c, "g3_album_" + ("error" if key == "last_error" else key), name)
    @property
    def native_value(self):
        return getattr(self.player, self.key)
