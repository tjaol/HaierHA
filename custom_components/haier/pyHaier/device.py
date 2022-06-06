from abc import ABC
from typing import Any, Optional

from .const import *


from .client import HaierClient


class Device(ABC):
    def __init__(self, device_conf: dict[str, Any], client: HaierClient) -> None:
        self.device_id = device_conf.get("deviceId")
        self.device_name = device_conf.get("deviceName")
        self.device_type = device_conf.get("deviceType")
        self.online = device_conf.get("online")
        self.product_code = device_conf.get("productCodeT")
        self.product_name = device_conf.get("productNameT")
        self.permissions = device_conf.get("totalPermission")

        self._device_conf = device_conf
        self._state = None
        self._device_units = None
        self._client = client

    async def update(self):
        """Fetch state of the device from Haier Smart cloud.
        List of device_confs is also updated.
        """
        await self._client.update_confs()
        self._state = await self._client.fetch_device_state(self)

    async def _set(self, properties: dict[str, Any]):
        await self._client.set_device_state(self, properties)

    @property
    def on_off_status(self) -> Optional[bool]:
        """Return current power setting - True if the device is on, False otherwise."""
        if self._state is None:
            return None
        return bool(self._state.get(HVAC_ON_OFF_STATUS) == "true")

    @property
    def availiable(self) -> bool:
        """Return current reachability to the device"""
        if self.online is None or not self.online:
            return False

        return True


class HaierAC(Device):
    """Class for Haier Air Conditioning device. Currently supported and Tested with only TH Model device."""

    _availiable_modes = [
        HVAC_OPERATION_MODE_COOL,
        HVAC_OPERATION_MODE_DRY,
        HVAC_OPERATION_MODE_FAN,
    ]
    _availiable_wind_speed = [
        HVAC_WIND_SPEED_AUTO,
        HVAC_WIND_SPEED_HIGH,
        HVAC_WIND_SPEED_MID,
        HVAC_WIND_SPEED_LOW,
    ]

    _availiable_wind_direction_vertical = [
        HVAC_WIND_DIRECTION_VERTICAL_AUTO,
        HVAC_WIND_DIRECTION_VERTICAL_FIXED,
    ]

    _availiable_wind_direction_horizontal = [
        HVAC_WIND_DIRECTION_HORIZONTAL_AUTO,
        HVAC_WIND_DIRECTION_HORIZONTAL_FIXED,
    ]
    _support_self_cleaning = False
    _support_human_sensing = False
    _min_target_temp = 16
    _max_target_temp = 30

    _str_type_property = [
        HVAC_ON_OFF_STATUS,
        HVAC_OPERATION_MODE,
        HVAC_SELF_CLEANING_STATUS,
    ]

    _allow_properties = [
        HVAC_ON_OFF_STATUS,
        HVAC_OPERATION_MODE,
        HVAC_TARGET_TEMP,
        HVAC_WIND_SPEED,
        HVAC_WIND_DIRECTION_VERTICAL,
        HVAC_WIND_DIRECTION_HORIZONTAL,
        HVAC_HUMAN_SENSING_STATUS,
        HVAC_SELF_CLEANING_STATUS,
    ]
    # def __init__(self, device_conf: dict[str, Any], client: HaierClient) -> None:
    #     super().__init__(device_conf, client)

    @property
    def available_operation_modes(self) -> list[str]:
        """Return available operation modes."""
        return self._availiable_modes

    @property
    def operation_mode(self) -> Optional[int]:
        """Return current operation mode."""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_OPERATION_MODE))

    @property
    def target_temperature(self) -> Optional[int]:
        """Return target (set) temperture."""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_TARGET_TEMP))

    @property
    def room_temperature(self) -> Optional[int]:
        """Return current room temperture."""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_ROOM_TEMP))

    @property
    def available_wind_speed(self) -> int:
        return self._availiable_wind_speed

    @property
    def available_wind_direction_horizontal(self) -> list[int]:
        """Return available horizontal wind direction choices"""
        return self._availiable_wind_direction_horizontal

    @property
    def available_wind_direction_vertical(self) -> list[int]:
        """Return available vertical wind direction choices"""
        return self._availiable_wind_direction_vertical

    @property
    def wind_direction_horizontal(self) -> Optional[int]:
        """Return current horizon wind direction setting"""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_WIND_DIRECTION_HORIZONTAL))

    @property
    def wind_direction_vertical(self) -> Optional[int]:
        """Return current vertical wind direction setting"""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_WIND_DIRECTION_VERTICAL))

    @property
    def wind_speed(self) -> Optional[int]:
        """Return current wind speed setting"""
        if self._state is None:
            return None
        return int(self._state.get(HVAC_WIND_SPEED))

    @property
    def min_target_temp(self):
        """Return minimun target temperture that can be set."""
        return self._min_target_temp

    @property
    def max_target_temp(self):
        """Return maximum target temperture that can be set."""
        return self._max_target_temp

    async def set(self, properties: dict[str:Any]):
        # Format and validate properties
        for k in properties.keys():

            # some properties needs to be string type
            if k in self._str_type_property:
                properties[k] = str(properties[k]).lower()

            if k not in self._allow_properties:
                raise ValueError("Invalid Property {k}")

            if k == HVAC_TARGET_TEMP and (
                properties[k] < self._min_target_temp
                or properties[k] > self._max_target_temp
            ):
                raise ValueError(
                    "Target temperature must in between {self._min_target_temp} <= x <= {self._max_target_temp}"
                )

        await self._set(properties)
