"""Config flow for smartlife."""
from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol
from io import BytesIO
from tuya_sharing import LoginControl

from .const import (
    DOMAIN,
    CONF_USER_CODE,
    LOGGER,
    CONF_CLIENT_ID,
    CONF_SCHEMA

)

APP_QR_CODE_HEADER = "tuyaSmart--qrLogin?token="


class SmartlifeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """smartlife Config Flow."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_code: str | None = None
        self._qr_code: str | None = None
        self.login_control = LoginControl()

    async def async_step_user(self, user_input=None):
        """Step user."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            self._user_code = user_input[CONF_USER_CODE]
            response = await self.hass.async_add_executor_job(self.login_control.qr_code, CONF_CLIENT_ID, CONF_SCHEMA,
                                                              self._user_code)
            LOGGER.debug("qr_code response = %s", response)
            if response.get("success", False):
                qr_code = response["result"]["qrcode"]
                self._qr_code = qr_code
                LOGGER.debug("qr_code=%s", qr_code)
                img = _generate_qr_code(APP_QR_CODE_HEADER + qr_code)
                return self.async_show_form(
                    step_id="scan",
                    description_placeholders={
                        "qr_code": img
                    },
                )
            errors["base"] = "login_error"
            placeholders = {
                "msg": response.get("msg"),
                "code": response.get("code")
            }

        if user_input is None:
            user_input = {}
            self._user_code = None
            self._qr_code = None

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_CODE, default=user_input.get(CONF_USER_CODE, "")
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_scan(self, user_input=None):
        # 调用查询登陆结果接口
        ret, info = await self.hass.async_add_executor_job(self.login_control.login_result,
                                                           self._qr_code, CONF_CLIENT_ID,
                                                           self._user_code)
        LOGGER.debug("login ret = %s, info = %s", ret, info)
        if ret:
            token_info = {
                "t": info.get("t"),
                "uid": info.get("uid"),
                "expire_time": info.get("expire_time"),
                "access_token": info.get("access_token"),
                "refresh_token": info.get("refresh_token"),
            }
            return self.async_create_entry(
                title=info.get("username"),
                data={
                    "user_code": self._user_code,
                    "token_info": token_info,
                    "terminal_id": info.get("terminal_id"),
                    "endpoint": info.get("endpoint")
                }
            )

        img = _generate_qr_code(APP_QR_CODE_HEADER + self._qr_code)
        return self.async_show_form(
            step_id="scan",
            errors={"base": "login_error"},
            description_placeholders={
                "qr_code": img,
                "msg": info.get("msg"),
                "code": info.get("code")
            },
        )


def _generate_qr_code(data: str) -> str:
    """Generate a base64 PNG string represent QR Code image of data."""
    import pyqrcode  # pylint: disable=import-outside-toplevel

    qr_code = pyqrcode.create(data)

    with BytesIO() as buffer:
        qr_code.svg(file=buffer, scale=4)
        return str(
            buffer.getvalue()
            .decode("ascii")
            .replace("\n", "")
            .replace(
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<svg xmlns="http://www.w3.org/2000/svg"'
                ),
                "<svg",
            )
        )
