import logging
import urllib.error

import voluptuous as vol
from homeassistant import config_entries

from .daikin_g3.community import CommunityAdapter
from .daikin_g3.preflight import probe
from .daikin_g3.protocol import CommandError, ProtocolError

_LOGGER = logging.getLogger(__name__)


class G3ConfigFlow(config_entries.ConfigFlow, domain="daikin_g3"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            stage = "device URL"
            try:
                adapter = await self.hass.async_add_executor_job(
                    CommunityAdapter, user_input["url"], user_input.get("password") or None
                )
                stage = "authenticated G3 identity and read-only protocol probe"
                result = await probe(adapter)
            except ValueError as exc:
                errors["base"] = "invalid_url" if stage == "device URL" else "unsupported_device"
                _LOGGER.warning("G3 setup rejected at %s (%s)", stage, type(exc).__name__)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    errors["base"] = "invalid_auth"
                elif exc.code in (404, 405):
                    errors["base"] = "unsupported_api"
                elif exc.code == 503:
                    errors["base"] = "device_busy"
                else:
                    errors["base"] = "cannot_connect"
                _LOGGER.warning(
                    "G3 setup failed at %s (HTTP status=%s)", stage, exc.code
                )
            except CommandError as exc:
                errors["base"] = "device_busy" if exc.code == "busy" else "invalid_protocol"
                _LOGGER.warning("G3 setup command rejected at %s (%s)", stage, exc.code)
            except ProtocolError as exc:
                errors["base"] = "invalid_protocol"
                _LOGGER.warning("G3 setup protocol failure at %s (%s)", stage, type(exc).__name__)
            except (OSError, TimeoutError) as exc:
                errors["base"] = "cannot_connect"
                _LOGGER.warning("G3 setup transport failure at %s (%s)", stage, type(exc).__name__)
            except Exception as exc:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unexpected G3 setup failure at %s (%s)", stage, type(exc).__name__)
            else:
                self._async_abort_entries_match({"url": adapter.base_url})
                return self.async_create_entry(
                    title=adapter.base_url,
                    data={**user_input, "url": adapter.base_url},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("url"): str,
                    vol.Optional("password", default=""): str,
                }
            ),
            errors=errors,
        )
