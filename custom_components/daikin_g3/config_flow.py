import voluptuous as vol
from homeassistant import config_entries
from .daikin_g3.community import CommunityAdapter

class G3ConfigFlow(config_entries.ConfigFlow, domain="daikin_g3"):
    VERSION=1

    async def async_step_user(self,user_input=None):
        errors={}
        if user_input is not None:
            try:
                adapter=await self.hass.async_add_executor_job(CommunityAdapter,user_input["url"],user_input.get("password"))
                await adapter.info()
                await adapter.capabilities()
            except ValueError:
                errors["base"]="invalid_url"
            except Exception:
                errors["base"]="cannot_connect"
            else:
                self._async_abort_entries_match({"url":adapter.base_url})
                return self.async_create_entry(title=adapter.base_url,data={**user_input,"url":adapter.base_url})
        return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required("url"):str,vol.Optional("password",default=""):str}),errors=errors)
