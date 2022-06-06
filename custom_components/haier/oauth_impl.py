"""Local implementation of OAuth2 specific to Ondilo to hard code client id and secret and return a proper name."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

from .const import (
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_CLIENTID,
    OAUTH2_CLIENTSECRET,
    OAUTH2_TOKEN,
)


class HaierOauth2Implementation(LocalOAuth2Implementation):
    """Local implementation of OAuth2 specific to Haier to hard code client id and secret and return a proper name."""

    scope = "BLUEENER"

    def __init__(self, hass: HomeAssistant) -> None:
        """Just init default class with default values."""
        super().__init__(
            hass,
            DOMAIN,
            OAUTH2_CLIENTID,
            OAUTH2_CLIENTSECRET,
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        )

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return "Haier"

    # @property
    # def extra_authorize_data(self) -> dict:
    #     """Extra data that needs to be appended to the authorize url."""
    #     return {"scope": "BLUENEER", "Test": "1"}
