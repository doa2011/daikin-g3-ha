from homeassistant.components.switch import SwitchEntity
from .album_entities import AlbumEntity
async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data["album_controller"]
    async_add_entities([AlbumSwitch(c, False), AlbumSwitch(c, True)])
class AlbumSwitch(AlbumEntity, SwitchEntity):
    def __init__(self, c, shuffle):
        self.shuffle = shuffle
        self.init_album(c, "g3_album_shuffle" if shuffle else "g3_album", "随机播放" if shuffle else "电子相册")
    @property
    def is_on(self):
        return self.player.settings["shuffle"] if self.shuffle else self.player.running
    async def async_turn_on(self, **kwargs):
        if self.shuffle:
            self.controller.set_setting("shuffle", True)
        elif not self.player.running:
            await self.controller.start()
    async def async_turn_off(self, **kwargs):
        if self.shuffle:
            self.controller.set_setting("shuffle", False)
        else:
            await self.controller.stop()
