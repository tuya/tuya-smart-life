"""Support for smartlife Cover."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tuya_sharing import Manager, CustomerDevice

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantSmartLifeData
from .base import IntegerTypeData, SmartLifeEntity
from .const import DOMAIN, SMART_LIFE_DISCOVERY_NEW, DPCode, DPType


@dataclass
class SmartLifeCoverEntityDescription(CoverEntityDescription):
    """Describe an smartlife cover entity."""

    current_state: DPCode | None = None
    current_state_inverse: bool = False
    current_position: DPCode | tuple[DPCode, ...] | None = None
    set_position: DPCode | None = None
    open_instruction_value: str = "open"
    close_instruction_value: str = "close"
    stop_instruction_value: str = "stop"
    product_id: str = None
    work_state: str = None
    reverse: bool = True
    set_position_open_close: bool = True


COVERS: dict[str, tuple[SmartLifeCoverEntityDescription, ...]] = {
    # Curtain
    # Note: Multiple curtains isn't documented
    # https://developer.tuya.com/en/docs/iot/categorycl?id=Kaiuz1hnpo7df
    "cl": (
        # AM43 Blind drive motor
        # Note: Only product_id is "zah67ekd"
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL,
            product_id="zah67ekd",
            current_position=DPCode.PERCENT_STATE,
            set_position=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.BLIND,
            work_state=DPCode.WORK_STATE,
            reverse=False,
            set_position_open_close=False,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL,
            name="Curtain",
            current_state=DPCode.SITUATION_SET,
            current_position=(DPCode.PERCENT_CONTROL, DPCode.PERCENT_STATE),
            set_position=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL_2,
            name="Curtain 2",
            current_position=DPCode.PERCENT_STATE_2,
            set_position=DPCode.PERCENT_CONTROL_2,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL_3,
            name="Curtain 3",
            current_position=DPCode.PERCENT_STATE_3,
            set_position=DPCode.PERCENT_CONTROL_3,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.MACH_OPERATE,
            name="Curtain",
            current_position=DPCode.POSITION,
            set_position=DPCode.POSITION,
            device_class=CoverDeviceClass.CURTAIN,
            open_instruction_value="FZ",
            close_instruction_value="ZZ",
            stop_instruction_value="STOP",
        ),
        # switch_1 is an undocumented code that behaves identically to control
        # It is used by the Kogan Smart Blinds Driver
        SmartLifeCoverEntityDescription(
            key=DPCode.SWITCH_1,
            name="Blind",
            current_position=DPCode.PERCENT_CONTROL,
            set_position=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.BLIND,
        ),
    ),
    # Garage Door Opener
    # https://developer.tuya.com/en/docs/iot/categoryckmkzq?id=Kaiuz0ipcboee
    "ckmkzq": (
        SmartLifeCoverEntityDescription(
            key=DPCode.SWITCH_1,
            name="Door",
            current_state=DPCode.DOORCONTACT_STATE,
            current_state_inverse=True,
            device_class=CoverDeviceClass.GARAGE,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.SWITCH_2,
            name="Door 2",
            current_state=DPCode.DOORCONTACT_STATE_2,
            current_state_inverse=True,
            device_class=CoverDeviceClass.GARAGE,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.SWITCH_3,
            name="Door 3",
            current_state=DPCode.DOORCONTACT_STATE_3,
            current_state_inverse=True,
            device_class=CoverDeviceClass.GARAGE,
        ),
    ),
    # Curtain Switch
    # https://developer.tuya.com/en/docs/iot/category-clkg?id=Kaiuz0gitil39
    "clkg": (
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL,
            name="Curtain",
            current_position=DPCode.PERCENT_CONTROL,
            set_position=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL_2,
            name="Curtain 2",
            current_position=DPCode.PERCENT_CONTROL_2,
            set_position=DPCode.PERCENT_CONTROL_2,
            device_class=CoverDeviceClass.CURTAIN,
        ),
    ),
    # Curtain Robot
    # Note: Not documented
    "jdcljqr": (
        SmartLifeCoverEntityDescription(
            key=DPCode.CONTROL,
            current_position=DPCode.PERCENT_STATE,
            set_position=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.CURTAIN,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up smartlife cover dynamically through smartlife discovery."""
    hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered smartlife cover."""
        entities: list[SmartLifeCoverEntity] = []
        for device_id in device_ids:
            device = hass_data.manager.device_map[device_id]
            if descriptions := COVERS.get(device.category):
                for description in descriptions:
                    if (
                        description.key in device.function
                        or description.key in device.status_range
                    ):
                        if description.product_id is None or description.product_id == device.product_id:
                            entities.append(
                                SmartLifeCoverEntity(device, hass_data.manager, description)
                            )
                            if description.product_id:
                                break

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SMART_LIFE_DISCOVERY_NEW, async_discover_device)
    )


class SmartLifeCoverEntity(SmartLifeEntity, CoverEntity):
    """smartlife Cover Device."""

    _current_position: IntegerTypeData | None = None
    _set_position: IntegerTypeData | None = None
    _tilt: IntegerTypeData | None = None
    entity_description: SmartLifeCoverEntityDescription

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: SmartLifeCoverEntityDescription,
    ) -> None:
        """Init smartlife Cover."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"
        self._attr_supported_features = CoverEntityFeature(0)
        self._send_position = None

        # Check if this cover is based on a switch or has controls
        if self.find_dpcode(description.key, prefer_function=True):
            if device.function[description.key].type == "Boolean":
                self._attr_supported_features |= (
                    CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
                )
            elif enum_type := self.find_dpcode(
                description.key, dptype=DPType.ENUM, prefer_function=True
            ):
                if description.open_instruction_value in enum_type.range:
                    self._attr_supported_features |= CoverEntityFeature.OPEN
                if description.close_instruction_value in enum_type.range:
                    self._attr_supported_features |= CoverEntityFeature.CLOSE
                if description.stop_instruction_value in enum_type.range:
                    self._attr_supported_features |= CoverEntityFeature.STOP

        # Determine type to use for setting the position
        if int_type := self.find_dpcode(
            description.set_position, dptype=DPType.INTEGER, prefer_function=True
        ):
            self._attr_supported_features |= CoverEntityFeature.SET_POSITION
            self._set_position = int_type
            # Set as default, unless overwritten below
            self._current_position = int_type

        # Determine type for getting the position
        if int_type := self.find_dpcode(
            description.current_position, dptype=DPType.INTEGER, prefer_function=True
        ):
            self._current_position = int_type

        # Determine type to use for setting the tilt
        if int_type := self.find_dpcode(
            (DPCode.ANGLE_HORIZONTAL, DPCode.ANGLE_VERTICAL),
            dptype=DPType.INTEGER,
            prefer_function=True,
        ):
            self._attr_supported_features |= CoverEntityFeature.SET_TILT_POSITION
            self._tilt = int_type

    @property
    def current_cover_position(self) -> int | None:
        """Return cover current position."""
        if self._current_position is None:
            return None

        if (position := self.device.status.get(self._current_position.dpcode)) is None:
            return None

        return round(
            self._current_position.remap_value_to(position, 0, 100, reverse=self.entity_description.reverse)
        )

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self._tilt is None:
            return None

        if (angle := self.device.status.get(self._tilt.dpcode)) is None:
            return None

        return round(self._tilt.remap_value_to(angle, 0, 100))

    @property
    def is_opening(self):
        """Return if cover is opening."""
        if self.entity_description.work_state is None:
            return None

        control = self.device.status.get(self.entity_description.key)
        set_position = self._send_position or self.device.status.get(
            self._set_position.dpcode
        )
        state = self.device.status.get(self.entity_description.work_state)

        return (
            control == "open"
            and state == "opening"
            and (set_position is None or set_position != self.current_cover_position)
        )

    @property
    def is_closing(self):
        """Return if cover is closing."""
        if self.entity_description.work_state is None:
            return None

        control = self.device.status.get(self.entity_description.key)
        set_position = self._send_position or self.device.status.get(
            self._set_position.dpcode
        )
        state = self.device.status.get(self.entity_description.work_state)

        return (
            control == "close"
            and state == "closing"
            and (set_position is None or set_position != self.current_cover_position)
        )

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed."""
        if (
            self.entity_description.current_state is not None
            and (
                current_state := self.device.status.get(
                    self.entity_description.current_state
                )
            )
            is not None
        ):
            return self.entity_description.current_state_inverse is not (
                current_state in (True, "fully_close")
            )

        if (position := self.current_cover_position) is not None:
            return position == 0

        return None

    def open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        value: bool | str = True
        if self.find_dpcode(
            self.entity_description.key, dptype=DPType.ENUM, prefer_function=True
        ):
            value = self.entity_description.open_instruction_value

        commands: list[dict[str, str | int]] = [
            {"code": self.entity_description.key, "value": value}
        ]
        if self._set_position is not None and self.entity_description.set_position_open_close:
            self._send_position = round(
                self._set_position.remap_value_from(
                    100, 0, 100, reverse=self.entity_description.reverse
                ),
            )
            commands.append(
                {
                    "code": self._set_position.dpcode,
                    "value": self._send_position,
                }
            )

        self._send_command(commands)
        self.async_schedule_update_ha_state()

    def close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        value: bool | str = False
        if self.find_dpcode(
            self.entity_description.key, dptype=DPType.ENUM, prefer_function=True
        ):
            value = self.entity_description.close_instruction_value

        commands: list[dict[str, str | int]] = [
            {"code": self.entity_description.key, "value": value}
        ]

        if self._set_position is not None and self.entity_description.set_position_open_close:
            self._send_position = round(
                self._set_position.remap_value_from(
                    0, 0, 100, reverse=self.entity_description.reverse
                ),
            )
            commands.append(
                {
                    "code": self._set_position.dpcode,
                    "value": self._send_position,
                }
            )

        self._send_command(commands)
        self.async_schedule_update_ha_state()

    def set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if self._set_position is None:
            raise RuntimeError(
                "Cannot set position, device doesn't provide methods to set it"
            )

        self._send_position = round(
            self._set_position.remap_value_from(
                kwargs[ATTR_POSITION], 0, 100, reverse=self.entity_description.reverse
            )
        )
        self._send_command(
            [
                {
                    "code": self._set_position.dpcode,
                    "value": self._send_position,
                }
            ]
        )
        self.async_schedule_update_ha_state()

    def stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self._send_command(
            [
                {
                    "code": self.entity_description.key,
                    "value": self.entity_description.stop_instruction_value,
                }
            ]
        )
        self.async_schedule_update_ha_state()

    def set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        if self._tilt is None:
            raise RuntimeError(
                "Cannot set tilt, device doesn't provide methods to set it"
            )

        self._send_command(
            [
                {
                    "code": self._tilt.dpcode,
                    "value": round(
                        self._tilt.remap_value_from(kwargs[ATTR_TILT_POSITION], 0, 100, reverse=self.entity_description.reverse)
                    ),
                }
            ]
        )
        self.async_schedule_update_ha_state()
