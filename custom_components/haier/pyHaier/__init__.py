from typing import List

from aiohttp import ClientSession

from .client import HaierClient
from .const import *
from .device import *


async def get_devices(client: ClientSession, haier_client: HaierClient) -> list[Device]:
    _client = haier_client
    await _client.update_confs()

    devices = []
    for conf in _client.device_confs:
        if conf["deviceType"] == DEVICE_TYPE_HVAC:
            devices.append(HaierAC(conf, _client))
    return devices
