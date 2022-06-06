"""Config flow for Haier integration."""
from __future__ import annotations

import logging
from typing import Any

from yarl import URL

from homeassistant import config_entries, core, data_entry_flow
from homeassistant.components.hassio import HassioServiceInfo
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from .const import DOMAIN, TYPE_LOCAL, TYPE_OAUTH2
from .oauth_impl import HaierOauth2Implementation

_LOGGER = logging.getLogger(__name__)


async def async_verify_local_connection(hass: core.HomeAssistant, host: str):
    """Verify that a local connection works."""
    websession = aiohttp_client.async_get_clientsession(hass)
    # _LOGGER.info("async_verify_local")
    return True


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for Haier."""

    DOMAIN = DOMAIN
    VERSION = 1
    host = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {"scope": "{SCOPE}"}

    async def async_step_user(self, user_input=None):
        _LOGGER.info("async_step_user")
        """Handle a flow start."""
        # Only allow 1 instance.
        await self.async_set_unique_id(DOMAIN)
        if (
            self._async_current_entries()
            and self.source != config_entries.SOURCE_REAUTH
        ):
            return self.async_abort(reason="single_instance_allowed")

        self.async_register_implementation(
            self.hass,
            HaierOauth2Implementation(self.hass),
        )

        return await super().async_step_user(user_input)

    async def async_step_auth(self, user_input=None):
        _LOGGER.info("async_step_auth")
        """Handle authorize step."""

        result = await super().async_step_auth(user_input)

        if result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP:
            self.host = str(URL(result["url"]).with_path(""))

        return result

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")

        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict) -> FlowResult:
        """Create an entry for the flow.

        Ok to override if you want to fetch extra info or even add another step.
        """
        _LOGGER.info("async_oauth_create_entry")
        data["type"] = TYPE_OAUTH2
        data["host"] = self.host

        existing_entry = await self.async_set_unique_id(DOMAIN)
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title=self.flow_impl.name, data=data)

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Import data."""
        # Only allow 1 instance.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if not await async_verify_local_connection(self.hass, user_input["host"]):
            self.logger.warning(
                "Aborting import of Almond because we're unable to connect"
            )
            return self.async_abort(reason="cannot_connect")

        return self.async_create_entry(
            title="Configuration.yaml",
            data={"type": TYPE_LOCAL, "host": user_input["host"]},
        )

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
        """Receive a Hass.io discovery."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self.hassio_discovery = discovery_info.config

        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input=None):
        """Confirm a Hass.io discovery."""
        data = self.hassio_discovery

        if user_input is not None:
            return self.async_create_entry(
                title=data["addon"],
                data={
                    "is_hassio": True,
                    "type": TYPE_LOCAL,
                    "host": f"http://{data['host']}:{data['port']}",
                },
            )

        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"addon": data["addon"]},
        )


# class CannotConnect(HomeAssistantError):
#     """Error to indicate we cannot connect."""


# class InvalidAuth(HomeAssistantError):
#     """Error to indicate there is invalid auth."""
