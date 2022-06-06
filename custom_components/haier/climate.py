"""Platform for climate integration."""
from __future__ import annotations
import asyncio

from datetime import timedelta
from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    ClimateEntityFeature,
    HVACMode,
)
from . import HaierDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging
from .const import DOMAIN
from .pyHaier.device import HaierAC
from .pyHaier import (
    HVAC_OPERATION_MODE_DRY,
    HVAC_OPERATION_MODE_COOL,
    HVAC_OPERATION_MODE_FAN,
    HVAC_WIND_DIRECTION_VERTICAL_AUTO,
    HVAC_WIND_DIRECTION_VERTICAL_FIXED,
    HVAC_WIND_DIRECTION_HORIZONTAL_AUTO,
    HVAC_WIND_DIRECTION_HORIZONTAL_FIXED,
    HVAC_WIND_DIRECTION_HORIZONTAL,
    HVAC_WIND_DIRECTION_VERTICAL,
    HVAC_WIND_SPEED_AUTO,
    HVAC_WIND_SPEED_HIGH,
    HVAC_WIND_SPEED_MID,
    HVAC_WIND_SPEED_LOW,
    HVAC_ON_OFF_STATUS,
    HVAC_OPERATION_MODE,
    HVAC_WIND_SPEED,
    HVAC_TARGET_TEMP,
)

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


HVAC_MODE_LOOKUP = {
    HVAC_OPERATION_MODE_DRY: HVACMode.DRY,
    HVAC_OPERATION_MODE_COOL: HVACMode.COOL,
    HVAC_OPERATION_MODE_FAN: HVACMode.FAN_ONLY,
}
ATA_HVAC_MODE_REVERSE_LOOKUP = {v: k for k, v in HVAC_MODE_LOOKUP.items()}

HVAC_VERTICAL_SWING_LOOKUP = {
    HVAC_WIND_DIRECTION_VERTICAL_AUTO: "Auto",
    HVAC_WIND_DIRECTION_VERTICAL_FIXED: "Fixed",
}
ATA_HVAC_VERTICAL_SWING_LOOKUP = {v: k for k, v in HVAC_VERTICAL_SWING_LOOKUP.items()}

HVAC_FAN_SPEED_LOOKUP = {
    HVAC_WIND_SPEED_AUTO: "Auto",
    HVAC_WIND_SPEED_HIGH: "High",
    HVAC_WIND_SPEED_MID: "Medium",
    HVAC_WIND_SPEED_LOW: "Low",
}
ATA_HVAC_FAN_SPEED_LOOKUP = {v: k for k, v in HVAC_FAN_SPEED_LOOKUP.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up haier cloud device climate based on config_entry."""
    devices = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [HaierClimate(d, d.device) for d in devices],
        True,
    )

    # platform = entity_platform.async_get_current_platform()
    # platform.async_register_entity_service(
    #     SERVICE_SET_VANE_HORIZONTAL,
    #     {vol.Required(CONF_POSITION): cv.string},
    #     "async_set_vane_horizontal",
    # )
    # platform.async_register_entity_service(
    #     SERVICE_SET_VANE_VERTICAL,
    #     {vol.Required(CONF_POSITION): cv.string},
    #     "async_set_vane_vertical",
    # )


class HaierClimate(ClimateEntity):

    _attr_temperature_unit = TEMP_CELSIUS
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_supported_features = (
        ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.SWING_MODE
    )
    _attr_swing_modes = ["Off", "Vertical", "Horizontal", "Both"]
    # _attr_max_temp = 30
    # _attr_min_temp = 16
    # _attr_fan_modes = [1, 2, 3, 5]
    # _attr_fan_mode = 1
    # _attr_swing_modes = [0, 8]
    # _attr_swing_mode = 0

    def __init__(self, device: HaierDevice, hvac_device: HaierAC) -> None:
        """Initialize the climate."""
        self.api = device
        self._base_device = self.api.device
        self._device = hvac_device

        self._attr_name = device.name
        self._attr_unique_id = self.api.device.device_id

    async def async_update(self):
        """Update state from cloud."""
        await self.api.async_update()

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self.api.device_info

    # @property
    # def target_temperature_step(self) -> float | None:
    #     """Return the supported step of target temperature."""
    #     return self._base_device.temperature_increment

    # @property
    # def extra_state_attributes(self) -> dict[str, Any] | None:
    #     """Return the optional state attributes with device specific additions."""
    #     attr = {}

    #     if vane_horizontal := self._device.vane_horizontal:
    #         attr.update(
    #             {
    #                 ATTR_VANE_HORIZONTAL: vane_horizontal,
    #                 ATTR_VANE_HORIZONTAL_POSITIONS: self._device.vane_horizontal_positions,
    #             }
    #         )

    #     if vane_vertical := self._device.vane_vertical:
    #         attr.update(
    #             {
    #                 ATTR_VANE_VERTICAL: vane_vertical,
    #                 ATTR_VANE_VERTICAL_POSITIONS: self._device.vane_vertical_positions,
    #             }
    #         )
    #     return attr

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        mode = self._device.operation_mode
        # _LOGGER.info("onOffStatus " + str(self._device.on_off_status))
        if not self._device.on_off_status or mode is None:
            # _LOGGER.info("HVAC is OFF")
            return HVACMode.OFF
        return HVAC_MODE_LOOKUP.get(mode)

    def _apply_set_hvac_mode(self, hvac_mode: str, set_dict: dict[str, Any]) -> None:
        """Apply hvac mode changes to a dict used to call _device.set."""
        if hvac_mode == HVACMode.OFF:
            set_dict[HVAC_ON_OFF_STATUS] = False
            return

        operation_mode = ATA_HVAC_MODE_REVERSE_LOOKUP.get(hvac_mode)
        if operation_mode is None:
            raise ValueError(f"Invalid hvac_mode [{hvac_mode}]")

        set_dict[HVAC_OPERATION_MODE] = operation_mode
        if self.hvac_mode == HVACMode.OFF:
            set_dict[HVAC_ON_OFF_STATUS] = True

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        set_dict = {}
        self._apply_set_hvac_mode(hvac_mode, set_dict)
        await self._device.set(set_dict)
        await asyncio.sleep(5)
        self._force_update_entity()

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac operation modes."""
        return [HVACMode.OFF] + [
            HVAC_MODE_LOOKUP.get(mode)
            for mode in self._device.available_operation_modes
        ]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._device.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._device.target_temperature

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        set_dict = {}
        if ATTR_HVAC_MODE in kwargs:
            self._apply_set_hvac_mode(
                kwargs.get(ATTR_HVAC_MODE, self.hvac_mode), set_dict
            )

        if ATTR_TEMPERATURE in kwargs:
            set_dict[HVAC_TARGET_TEMP] = int(kwargs.get(ATTR_TEMPERATURE))

        if set_dict:
            await self._device.set(set_dict)

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return HVAC_FAN_SPEED_LOOKUP.get(self._device.wind_speed)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._device.set(
            {HVAC_WIND_SPEED: ATA_HVAC_FAN_SPEED_LOOKUP.get(fan_mode)}
        )

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return [
            HVAC_FAN_SPEED_LOOKUP.get(mode)
            for mode in self._device.available_wind_speed
        ]

    # async def async_set_vane_horizontal(self, position: str) -> None:
    #     """Set horizontal vane position."""
    #     if position not in self._device.vane_horizontal_positions:
    #         raise ValueError(
    #             f"Invalid horizontal vane position {position}. Valid positions: [{self._device.vane_horizontal_positions}]."
    #         )
    #     await self._device.set({ata.PROPERTY_VANE_HORIZONTAL: position})

    # async def async_set_vane_vertical(self, position: str) -> None:
    #     """Set vertical vane position."""
    #     if position not in self._device.vane_vertical_positions:
    #         raise ValueError(
    #             f"Invalid vertical vane position {position}. Valid positions: [{self._device.vane_vertical_positions}]."
    #         )
    #     await self._device.set({ata.PROPERTY_VANE_VERTICAL: position})

    @property
    def swing_mode(self) -> str | None:
        """Return vertical vane position or mode."""
        swing_vertical = self._device.wind_direction_vertical
        swing_horizontal = self._device.wind_direction_horizontal
        if (
            swing_vertical == HVAC_WIND_DIRECTION_VERTICAL_FIXED
            and swing_horizontal == HVAC_WIND_DIRECTION_HORIZONTAL_FIXED
        ):
            return self._attr_swing_modes[0]  # Off

        elif (
            swing_vertical != HVAC_WIND_DIRECTION_VERTICAL_FIXED
            and swing_horizontal == HVAC_WIND_DIRECTION_HORIZONTAL_FIXED
        ):
            return self._attr_swing_modes[1]  # Vertical

        elif (
            swing_vertical == HVAC_WIND_DIRECTION_VERTICAL_FIXED
            and swing_horizontal != HVAC_WIND_DIRECTION_HORIZONTAL_FIXED
        ):
            return self._attr_swing_modes[2]  # Horizontal

        elif (
            swing_vertical != HVAC_WIND_DIRECTION_VERTICAL_FIXED
            and swing_horizontal != HVAC_WIND_DIRECTION_HORIZONTAL_FIXED
        ):
            return self._attr_swing_modes[3]  # Both

        return None

    async def async_set_swing_mode(self, swing_mode) -> None:
        set_dict = {}
        if swing_mode == self._attr_swing_modes[0]:  # Off
            set_dict = {
                HVAC_WIND_DIRECTION_HORIZONTAL: HVAC_WIND_DIRECTION_HORIZONTAL_FIXED,
                HVAC_WIND_DIRECTION_VERTICAL: HVAC_WIND_DIRECTION_VERTICAL_FIXED,
            }
        elif swing_mode == self._attr_swing_modes[1]:  # Vertical
            set_dict = {
                HVAC_WIND_DIRECTION_HORIZONTAL: HVAC_WIND_DIRECTION_HORIZONTAL_FIXED,
                HVAC_WIND_DIRECTION_VERTICAL: HVAC_WIND_DIRECTION_VERTICAL_AUTO,
            }
        elif swing_mode == self._attr_swing_modes[2]:  # Horizontal
            set_dict = {
                HVAC_WIND_DIRECTION_HORIZONTAL: HVAC_WIND_DIRECTION_HORIZONTAL_AUTO,
                HVAC_WIND_DIRECTION_VERTICAL: HVAC_WIND_DIRECTION_VERTICAL_FIXED,
            }
        elif swing_mode == self._attr_swing_modes[3]:  # Both
            set_dict = {
                HVAC_WIND_DIRECTION_HORIZONTAL: HVAC_WIND_DIRECTION_HORIZONTAL_AUTO,
                HVAC_WIND_DIRECTION_VERTICAL: HVAC_WIND_DIRECTION_VERTICAL_AUTO,
            }

        await self._device.set(set_dict)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set({"onOffStatus": True})

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set({"onOffStatus": False})

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        min_value = self._device.min_target_temp
        if min_value is not None:
            return min_value
        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        max_value = self._device.max_target_temp
        if max_value is not None:
            return max_value

        return DEFAULT_MAX_TEMP

    def _force_update_entity(self):
        self.async_schedule_update_ha_state(True)
