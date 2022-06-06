""" Haier API Access """
from abc import abstractmethod
from datetime import datetime
import hashlib
import json
from typing import Any, Optional
import logging
from aiohttp import ClientSession, web
from .const import *
import itertools

BASE_URL = "https://uws-sea.haieriot.net"
API_DIR = "/dcs/third-party-cloud/"

# API_PORT
DEVICE_LIST_API = "add/user/third-party/device"
DEVICE_DETAIL_API = "get/device/detail"
DEVICE_STATUS_API = "get/device/status"
DEVICE_CONTROL_API = "update/device/cmd"


_LOGGER = logging.getLogger(__name__)


class HaierClient:
    def __init__(self, session: ClientSession):
        # self._session = ClientSession()
        self._session = session
        self._last_user_update = None
        self._last_conf_update = None
        self._device_confs: list[dict[str, Any]] = []
        self._account: Optional[dict[str, Any]] = None
        self._sequence_iter = itertools.count()

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    def _generate_sequence_id(self) -> str:
        sequence_id = str(self.timestamp) + str(next(self._sequence_iter)).rjust(6, "0")
        # _LOGGER.info("sequence id " + str(sequence_id))
        return sequence_id

    async def create_header(self, API_PORT: str, body="") -> dict[str, str]:
        curTimestamp = self.timestamp
        token = await self.async_get_access_token()
        return {
            "Connection": "keep-alive",
            "systemId": SYSTEM_ID,
            "appVersion": APP_VERSION,
            "clientId": CLIENT_ID,
            "sequenceId": self._generate_sequence_id(),
            "accessToken": token,
            "sign": self.calculate_sign(API_PORT, curTimestamp, body),
            "timestamp": str(curTimestamp),
            "language": "zh-cn",
            "timezone": "+7",
            "appKey": APP_KEY,
            "Content-Encoding": "utf-8",
            "Content-Type": "application/json",
        }

    def calculate_sign(self, API_PORT: str, timestamp: int, body) -> str:
        bodyStr = json.dumps(body).replace(" ", "")
        if bodyStr == '""':
            bodyStr = ""

        sign = API_PORT + bodyStr + SYSTEM_ID + SYSTEM_KEY + str(timestamp)
        # print("Sign = " + sign)
        return hashlib.sha256(sign.encode()).hexdigest()

    @property
    def timestamp(self) -> int:
        return int(round(datetime.now().timestamp()))

    @property
    def device_confs(self) -> list[dict[Any, Any]]:
        """Return device configurations."""
        return self._device_confs

    async def update_confs(self):
        await self._fetch_device_confs()

    async def _fetch_device_confs(self):
        """Fetch all configured devices."""
        url = BASE_URL + API_DIR + DEVICE_LIST_API
        header = await self.create_header(API_DIR + DEVICE_LIST_API)

        async with self._session.post(
            url, headers=header, raise_for_status=True
        ) as resp:
            respJson = await resp.json()
            if respJson["retCode"] != RET_CODE_OK:
                raise web.HTTPUnauthorized(
                    reason=self.get_error_reason(respJson["retCode"])
                )

            self._device_confs = respJson["payload"]

    async def fetch_device_state(self, device) -> Optional[dict[str, Any]]:
        """Fetch state information of a device.
        This method should not be called more than once a minute. Rate
        limiting is left to the caller.
        """

        url = BASE_URL + API_DIR + DEVICE_STATUS_API
        body = {"deviceId": device.device_id, "part": 0}
        header = await self.create_header(API_DIR + DEVICE_STATUS_API, body)
        async with self._session.post(
            url, headers=header, json=body, raise_for_status=True
        ) as resp:
            respJson = await resp.json()
            if respJson["retCode"] != RET_CODE_OK:
                raise web.HTTPUnauthorized(
                    reason=self.get_error_reason(respJson["retCode"])
                )

            return respJson["payload"]["reported"]

    async def set_device_state(self, device, properties: dict[str, Any]) -> None:
        """set state information of a device."""

        url = BASE_URL + API_DIR + DEVICE_CONTROL_API
        body = {
            "deviceId": device.device_id,
            "cmdName": "grSetDAC",
            "cmdArgs": properties,
        }
        _LOGGER.info(body)
        header = await self.create_header(API_DIR + DEVICE_CONTROL_API, body)
        async with self._session.post(
            url, headers=header, json=body, raise_for_status=True
        ) as resp:
            respJson = await resp.json()
            if respJson["retCode"] != RET_CODE_OK:
                raise web.HTTPUnauthorized(
                    reason=self.get_error_reason(
                        respJson["retCode"], respJson["retInfo"]
                    )
                )

            return respJson["retCode"]

    def get_error_reason(self, errorcode, retinfo=""):
        if errorcode == RET_CODE_USER_ILLEGAL:
            return "User is illegal, Token expired?"
        elif errorcode == RET_CODE_USER_NOT_MATCH_DEVICE:
            return "The current user does not match the device"
        else:
            return "Unknown Error : {errorcode} {retinfo}"
