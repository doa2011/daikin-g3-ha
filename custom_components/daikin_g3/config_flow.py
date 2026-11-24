import logging
import urllib.error
from .daikin_g3.protocol import ProtocolError, CommandError
import voluptuous as vol
from homeassistant import config_entries
from .daikin_g3.community import CommunityAdapter

_LOGGER = logging.getLogger(__name__)

class G3ConfigFlow(config_entries.ConfigFlow, domain="daikin_g3"):
    VERSION=1

    async def async_step_user(self,user_input=None):
        errors={}
        if user_input is not None:
            stage = 'device URL'
            try:
                adapter=await self.hass.async_add_executor_job(CommunityAdapter,user_input["url"],user_input.get("password"))
                stage = 'GET /api/v1/info'
                await adapter.info()
                stage = 'GET /api/v1/capabilities'
                await adapter.capabilities()
            except ValueError as exc:
                errors["base"]="invalid_url" if stage == "device URL" else "cannot_connect"
                _LOGGER.warning("G3 setup failed at %s (%s)", stage, type(exc).__name__)
            except Exception as exc:
                status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
                if status in (401, 403):
                    errors["base"] = "invalid_auth"
                elif status == 503 or (isinstance(exc, CommandError) and exc.code == "busy"):
                    errors["base"] = "device_busy"
                elif status in (404, 405):
                    errors["base"] = "unsupported_api"
                elif isinstance(exc, ProtocolError):
                    errors["base"] = "invalid_protocol"
                else:
                    errors["base"] = "cannot_connect"
                # Do not log URLs, credentials, response bodies or exception text.
                status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
                _LOGGER.warning("G3 setup failed at %s (%s, HTTP status=%s)", stage, type(exc).__name__, status)
            else:
                self._async_abort_entries_match({"url":adapter.base_url})
                return self.async_create_entry(title=adapter.base_url,data={**user_input,"url":adapter.base_url})
        return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required("url"):str,vol.Optional("password",default=""):str}),errors=errors)
