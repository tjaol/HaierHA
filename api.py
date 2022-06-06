"""API for Netatmo bound to HASS OAuth."""

from aiohttp import ClientSession

from homeassistant.helpers import config_entry_oauth2_flow

from .pyHaier.client import HaierClient


class OAuth2SessionHaier(config_entry_oauth2_flow.OAuth2Session):
    """OAuth2Session for Haier."""

    async def force_refresh_token(self) -> None:
        """Force a token refresh."""
        new_token = await self.implementation.async_refresh_token(self.token)

        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, "token": new_token}
        )


class ConfigEntryHaierClient(HaierClient):
    """Provide Haier authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize auth."""
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        if not self._oauth_session.valid_token:
            await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]
