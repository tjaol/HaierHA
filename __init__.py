"""The Haier integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from http import HTTPStatus
import logging
from typing import Any

from aiohttp import ClientConnectionError, ClientSession
from async_timeout import timeout

from .oauth_impl import HaierOauth2Implementation
from .pyHaier.client import HaierClient
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_HOST,
    CONF_TYPE,
    EVENT_HOMEASSISTANT_START,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
    event,
    intent,
    network,
    storage,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import Throttle

from .api import ConfigEntryHaierClient, OAuth2SessionHaier
from .config_flow import ConfigFlow
from .const import DOMAIN, TYPE_LOCAL, TYPE_OAUTH2
from .pyHaier import get_devices
from .pyHaier.device import Device

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.CLIMATE]

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the component."""
    hass.data[DOMAIN] = {}
    _LOGGER.info("ASYNC Setup")

    ConfigFlow.async_register_implementation(hass, HaierOauth2Implementation(hass))

    if DOMAIN not in config:
        return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Haier from a config entry."""
    # TODO Store an API object for your platforms to access

    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    # hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    _LOGGER.info("ASYNC Setup entry")

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = aiohttp_client.async_get_clientsession(hass)
    oauth_session = OAuth2SessionHaier(hass, entry, implementation)
    haier_client = ConfigEntryHaierClient(session, oauth_session)

    _LOGGER.info(str(entry.data))
    token = entry.data["token"]["access_token"]
    _LOGGER.info("token = " + str(token))

    haier_devices = await haier_devices_setup(hass, oauth_session, haier_client)

    hass.data.setdefault(DOMAIN, {}).update({entry.entry_id: haier_devices})
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HaierDevice:
    """Haier Device instance. (Wrapper of pyHaier device)"""

    SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES

    def __init__(self, device: Device) -> None:
        self.device = device
        self.name = device.device_name
        self._available = True

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs):
        """Pull the latest data from haier cloud."""
        try:
            _LOGGER.info("Updating device %s", self.name)
            await self.device.update()
            self._available = True
        except ClientConnectionError:
            _LOGGER.warning("Connection failed for %s", self.name)
            self._available = False

    async def async_set(self, properties: dict[str, Any]):
        """Write state changes to the Haier API."""
        try:
            await self.device.set(properties)
            self._available = True
        except ClientConnectionError:
            _LOGGER.warning("Connection failed for %s", self.name)
            self._available = False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def device_id(self):
        """Return device ID."""
        return self.device.device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        model = None

        return DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            manufacturer="Haier",
            model=self.device.product_name,
            name=self.name,
        )


async def haier_devices_setup(
    hass,
    session: ClientSession,
    haier_client: HaierClient,
) -> list[HaierDevice]:
    """Query connected devices from haier cloud."""

    try:
        async with timeout(10):
            all_devices = await get_devices(
                session,
                haier_client
                # session,
                # conf_update_interval=timedelta(minutes=5),
                # device_set_debounce=timedelta(seconds=1),
            )
    except (asyncio.TimeoutError, ClientConnectionError) as ex:
        raise ConfigEntryNotReady() from ex

    # wrapped_devices = {}
    # for device_type, devices in all_devices.items():
    #     wrapped_devices[device_type] = [HaierDevice(device) for device in devices]

    wrapped_devices = []
    for d in all_devices:
        wrapped_devices.append(HaierDevice(d))
    return wrapped_devices
