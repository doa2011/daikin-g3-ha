"""HA album settings and shared entity state."""
from pathlib import Path
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from .daikin_g3.album import photos
from .daikin_g3.album_player import AlbumPlayer

DEFAULT = "/media/g3-album"

def scan_media(directory, roots):
    path = Path(directory).resolve(strict=True)
    if not any(path.is_relative_to(Path(root).resolve()) for root in roots):
        raise ValueError("album must be inside a configured HA media directory")
    return photos(path)

class AlbumController:
    def __init__(self, hass, entry, album):
        self.hass, self.entry = hass, entry
        self.listeners = set()
        opts = entry.options
        self.directories = list(opts.get("album_directories", [DEFAULT])) or [DEFAULT]
        settings = dict(opts.get("album_settings", {}))
        if settings.get("directory") not in self.directories:
            settings["directory"] = self.directories[0]
        roots = tuple(hass.config.media_dirs.values()) + ("/media",)
        self.player = AlbumPlayer(album, scan=lambda d: scan_media(d, roots),
                                  changed=self.notify, settings=settings)

    def notify(self):
        for callback in tuple(self.listeners):
            callback()

    def save(self):
        self.hass.config_entries.async_update_entry(self.entry, options={
            **self.entry.options, "album_directories": self.directories,
            "album_settings": dict(self.player.settings)})
        self.notify()

    async def set_directories(self, value):
        if self.player.running:
            raise HomeAssistantError("Stop album before changing directories")
        dirs = list(dict.fromkeys(x.strip() for x in value.split(";") if x.strip()))
        if not dirs:
            raise HomeAssistantError("Specify at least one album directory")
        try:
            for directory in dirs:
                await self.hass.async_add_executor_job(self.player.scan, directory)
        except (OSError, ValueError) as exc:
            raise HomeAssistantError(str(exc)) from exc
        self.directories = dirs
        if self.player.settings["directory"] not in dirs:
            self.player.settings["directory"] = dirs[0]
        self.save()
        await self.player.refresh()

    async def select(self, option):
        if self.player.running:
            raise HomeAssistantError("Stop album before changing source")
        if option not in self.directories:
            raise HomeAssistantError("Unknown album")
        self.player.settings["directory"] = option
        self.save()
        await self.player.refresh()

    async def start(self):
        try:
            await self.player.start_album(**self.player.settings)
        except (OSError, ValueError, RuntimeError) as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def stop(self):
        await self.player.stop_album()

    def set_setting(self, key, value):
        self.player.settings[key] = value
        self.save()

class AlbumEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def init_album(self, c, key, name):
        self.controller, self.player = c, c.player
        self._attr_unique_id = f"{c.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_suggested_object_id = key
        self._attr_device_info = DeviceInfo(identifiers={("daikin_g3", c.entry.entry_id)},
            name=c.entry.title, manufacturer="Daikin", model="G3")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.controller.listeners.add(self.async_write_ha_state)
        self.async_on_remove(lambda: self.controller.listeners.discard(self.async_write_ha_state))
