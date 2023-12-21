"""Support for smartlife (de)humidifiers."""
from __future__ import annotations

from dataclasses import dataclass

from tuya_sharing import Manager, CustomerDevice

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityDescription,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantSmartLifeData
from .base import IntegerTypeData, SmartLifeEntity
from .const import DOMAIN, SMART_LIFE_DISCOVERY_NEW, DPCode, DPType


@dataclass
class SmartLifeHumidifierEntityDescription(HumidifierEntityDescription):
    """Describe an smartlife (de)humidifier entity."""

    # DPCode, to use. If None, the key will be used as DPCode
    dpcode: DPCode | tuple[DPCode, ...] | None = None

    humidity: DPCode | None = None


HUMIDIFIERS: dict[str, SmartLifeHumidifierEntityDescription] = {
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    "cs": SmartLifeHumidifierEntityDescription(
        key=DPCode.SWITCH,
        dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
        humidity=DPCode.DEHUMIDITY_SET_VALUE,
        device_class=HumidifierDeviceClass.DEHUMIDIFIER,
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": SmartLifeHumidifierEntityDescription(
        key=DPCode.SWITCH,
        dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
        humidity=DPCode.HUMIDITY_SET,
        device_class=HumidifierDeviceClass.HUMIDIFIER,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up smartlife (de)humidifier dynamically through smartlife discovery."""
    hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered smartlife (de)humidifier."""
        entities: list[SmartLifeHumidifierEntity] = []
        for device_id in device_ids:
            device = hass_data.manager.device_map[device_id]
            if description := HUMIDIFIERS.get(device.category):
                if description.key in device.status or any(item in device.status for item in description.dpcode):
                    entities.append(
                        SmartLifeHumidifierEntity(device, hass_data.manager, description)
                    )
        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SMART_LIFE_DISCOVERY_NEW, async_discover_device)
    )


class SmartLifeHumidifierEntity(SmartLifeEntity, HumidifierEntity):
    """smartlife (de)humidifier Device."""

    _set_humidity: IntegerTypeData | None = None
    _switch_dpcode: DPCode | None = None
    entity_description: SmartLifeHumidifierEntityDescription

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: SmartLifeHumidifierEntityDescription,
    ) -> None:
        """Init smartlife (de)humidier."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

        # Determine main switch DPCode
        self._switch_dpcode = self.find_dpcode(
            description.dpcode or DPCode(description.key), prefer_function=True
        )

        # Determine humidity parameters
        if int_type := self.find_dpcode(
            description.humidity, dptype=DPType.INTEGER, prefer_function=True
        ):
            self._set_humidity = int_type
            self._attr_min_humidity = int(int_type.min_scaled)
            self._attr_max_humidity = int(int_type.max_scaled)

        # Determine mode support and provided modes
        if enum_type := self.find_dpcode(
            DPCode.MODE, dptype=DPType.ENUM, prefer_function=True
        ):
            self._attr_supported_features |= HumidifierEntityFeature.MODES
            self._attr_available_modes = enum_type.range

    @property
    def is_on(self) -> bool:
        """Return the device is on or off."""
        if self._switch_dpcode is None:
            return False
        return self.device.status.get(self._switch_dpcode, False)

    @property
    def mode(self) -> str | None:
        """Return the current mode."""
        return self.device.status.get(DPCode.MODE)

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""
        if self._set_humidity is None:
            return None

        humidity = self.device.status.get(self._set_humidity.dpcode)
        if humidity is None:
            return None

        return round(self._set_humidity.scale_value(humidity))

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._send_command([{"code": self._switch_dpcode, "value": True}])

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._send_command([{"code": self._switch_dpcode, "value": False}])

    def set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if self._set_humidity is None:
            raise RuntimeError(
                "Cannot set humidity, device doesn't provide methods to set it"
            )

        self._send_command(
            [
                {
                    "code": self._set_humidity.dpcode,
                    "value": self._set_humidity.scale_value_back(humidity),
                }
            ]
        )

    def set_mode(self, mode):
        """Set new target preset mode."""
        self._send_command([{"code": DPCode.MODE, "value": mode}])
