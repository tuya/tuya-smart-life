"""Support for smartlife select."""
from __future__ import annotations

from tuya_sharing import Manager, CustomerDevice

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantSmartLifeData
from .base import SmartLifeEntity
from .const import DOMAIN, SMART_LIFE_DISCOVERY_NEW, DPCode, DPType

# All descriptions can be found here. Mostly the Enum data types in the
# default instructions set of each category end up being a select.
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
SELECTS: dict[str, tuple[SelectEntityDescription, ...]] = {
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        SelectEntityDescription(
            key=DPCode.ALARM_VOLUME,
            name="Volume",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Coffee maker
    # https://developer.tuya.com/en/docs/iot/categorykfj?id=Kaiuz2p12pc7f
    "kfj": (
        SelectEntityDescription(
            key=DPCode.CUP_NUMBER,
            name="Cups",
            icon="mdi:numeric",
        ),
        SelectEntityDescription(
            key=DPCode.CONCENTRATION_SET,
            name="Concentration",
            icon="mdi:altimeter",
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key=DPCode.MATERIAL,
            name="Material",
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key=DPCode.MODE,
            name="Mode",
            icon="mdi:coffee",
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        SelectEntityDescription(
            key=DPCode.RELAY_STATUS,
            name="Power on behavior",
            entity_category=EntityCategory.CONFIG,
            translation_key="relay_status",
        ),
        SelectEntityDescription(
            key=DPCode.LIGHT_MODE,
            name="Indicator light mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="light_mode",
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    "qn": (
        SelectEntityDescription(
            key=DPCode.LEVEL,
            name="Temperature level",
            icon="mdi:thermometer-lines",
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    "sgbj": (
        SelectEntityDescription(
            key=DPCode.ALARM_VOLUME,
            name="Volume",
            entity_category=EntityCategory.CONFIG,
        ),
        SelectEntityDescription(
            key=DPCode.BRIGHT_STATE,
            name="Brightness",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        SelectEntityDescription(
            key=DPCode.IPC_WORK_MODE,
            name="IPC mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="ipc_work_mode",
        ),
        SelectEntityDescription(
            key=DPCode.DECIBEL_SENSITIVITY,
            name="Sound detection densitivity",
            icon="mdi:volume-vibrate",
            entity_category=EntityCategory.CONFIG,
            translation_key="decibel_sensitivity",
        ),
        SelectEntityDescription(
            key=DPCode.RECORD_MODE,
            name="Record mode",
            icon="mdi:record-rec",
            entity_category=EntityCategory.CONFIG,
            translation_key="record_mode",
        ),
        SelectEntityDescription(
            key=DPCode.BASIC_NIGHTVISION,
            name="Night vision",
            icon="mdi:theme-light-dark",
            entity_category=EntityCategory.CONFIG,
            translation_key="basic_nightvision",
        ),
        SelectEntityDescription(
            key=DPCode.BASIC_ANTI_FLICKER,
            name="Anti-flicker",
            icon="mdi:image-outline",
            entity_category=EntityCategory.CONFIG,
            translation_key="basic_anti_flicker",
        ),
        SelectEntityDescription(
            key=DPCode.MOTION_SENSITIVITY,
            name="Motion detection sensitivity",
            icon="mdi:motion-sensor",
            entity_category=EntityCategory.CONFIG,
            translation_key="motion_sensitivity",
        ),
    ),
    # IoT Switch?
    # Note: Undocumented
    "tdq": (
        SelectEntityDescription(
            key=DPCode.RELAY_STATUS,
            name="Power on behavior",
            entity_category=EntityCategory.CONFIG,
            translation_key="relay_status",
        ),
        SelectEntityDescription(
            key=DPCode.LIGHT_MODE,
            name="Indicator light mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="light_mode",
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    "tgkg": (
        SelectEntityDescription(
            key=DPCode.RELAY_STATUS,
            name="Power on behavior",
            entity_category=EntityCategory.CONFIG,
            translation_key="relay_status",
        ),
        SelectEntityDescription(
            key=DPCode.LIGHT_MODE,
            name="Indicator light mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="light_mode",
        ),
        SelectEntityDescription(
            key=DPCode.LED_TYPE_1,
            name="Light source type",
            entity_category=EntityCategory.CONFIG,
            translation_key="led_type",
        ),
        SelectEntityDescription(
            key=DPCode.LED_TYPE_2,
            name="Light 2 source type",
            entity_category=EntityCategory.CONFIG,
            translation_key="led_type",
        ),
        SelectEntityDescription(
            key=DPCode.LED_TYPE_3,
            name="Light 3 source type",
            entity_category=EntityCategory.CONFIG,
            translation_key="led_type",
        ),
    ),
    # Dimmer
    # https://developer.tuya.com/en/docs/iot/tgq?id=Kaof8ke9il4k4
    "tgq": (
        SelectEntityDescription(
            key=DPCode.LED_TYPE_1,
            name="Light source type",
            entity_category=EntityCategory.CONFIG,
            translation_key="led_type",
        ),
        SelectEntityDescription(
            key=DPCode.LED_TYPE_2,
            name="Light 2 source type",
            entity_category=EntityCategory.CONFIG,
            translation_key="led_type",
        ),
    ),
    # Fingerbot
    "szjqr": (
        SelectEntityDescription(
            key=DPCode.MODE,
            name="Mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="fingerbot_mode",
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        SelectEntityDescription(
            key=DPCode.CISTERN,
            name="Water tank adjustment",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:water-opacity",
            translation_key="vacuum_cistern",
        ),
        SelectEntityDescription(
            key=DPCode.COLLECTION_MODE,
            name="Dust collection mode",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:air-filter",
            translation_key="vacuum_collection",
        ),
        SelectEntityDescription(
            key=DPCode.MODE,
            name="Mode",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:layers-outline",
            translation_key="vacuum_mode",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45vs7vkge
    "fs": (
        SelectEntityDescription(
            key=DPCode.FAN_VERTICAL,
            name="Vertical swing flap angle",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:format-vertical-align-center",
            translation_key="fan_angle",
        ),
        SelectEntityDescription(
            key=DPCode.FAN_HORIZONTAL,
            name="Horizontal swing flap angle",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:format-horizontal-align-center",
            translation_key="fan_angle",
        ),
        SelectEntityDescription(
            key=DPCode.COUNTDOWN,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
        SelectEntityDescription(
            key=DPCode.COUNTDOWN_SET,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46o5mtfyc
    "cl": (
        SelectEntityDescription(
            key=DPCode.CONTROL_BACK_MODE,
            name="Motor mode",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:swap-horizontal",
            translation_key="curtain_motor_mode",
        ),
        SelectEntityDescription(
            key=DPCode.MODE,
            name="Mode",
            entity_category=EntityCategory.CONFIG,
            translation_key="curtain_mode",
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        SelectEntityDescription(
            key=DPCode.SPRAY_MODE,
            name="Spray mode",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:spray",
            translation_key="humidifier_spray_mode",
        ),
        SelectEntityDescription(
            key=DPCode.LEVEL,
            name="Spraying level",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:spray",
            translation_key="humidifier_level",
        ),
        SelectEntityDescription(
            key=DPCode.MOODLIGHTING,
            name="Moodlighting",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:lightbulb-multiple",
            translation_key="humidifier_moodlighting",
        ),
        SelectEntityDescription(
            key=DPCode.COUNTDOWN,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
        SelectEntityDescription(
            key=DPCode.COUNTDOWN_SET,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    "kj": (
        SelectEntityDescription(
            key=DPCode.COUNTDOWN,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
        SelectEntityDescription(
            key=DPCode.COUNTDOWN_SET,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
    ),
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    "cs": (
        SelectEntityDescription(
            key=DPCode.COUNTDOWN_SET,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
        SelectEntityDescription(
            key=DPCode.DEHUMIDITY_SET_ENUM,
            name="Target humidity",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:water-percent",
        ),
    ),
    # Smart Towel Rack
    # https://developer.tuya.com/en/docs/iot/categorymjj?id=Kakkmlm9k4cir
    "mjj": (
        SelectEntityDescription(
            key=DPCode.COUNTDOWN_SET,
            name="Countdown",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timer-cog-outline",
            translation_key="countdown",
        ),
    ),
}

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SELECTS["cz"] = SELECTS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SELECTS["pc"] = SELECTS["kg"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Smart Life select dynamically through Smart Life discovery."""
    hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Smart Life select."""
        entities: list[SmartLifeSelectEntity] = []
        for device_id in device_ids:
            device = hass_data.manager.device_map[device_id]
            if descriptions := SELECTS.get(device.category):
                for description in descriptions:
                    if description.key in device.status:
                        entities.append(
                            SmartLifeSelectEntity(
                                device, hass_data.manager, description
                            )
                        )

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SMART_LIFE_DISCOVERY_NEW, async_discover_device)
    )


class SmartLifeSelectEntity(SmartLifeEntity, SelectEntity):
    """Smart Life Select Entity."""

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: SelectEntityDescription,
    ) -> None:
        """Init Smart Life select."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

        self._attr_options: list[str] = []
        if enum_type := self.find_dpcode(
            description.key, dptype=DPType.ENUM, prefer_function=True
        ):
            self._attr_options = enum_type.range

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        # Raw value
        value = self.device.status.get(self.entity_description.key)
        if value is None or value not in self._attr_options:
            return None

        return value

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._send_command(
            [
                {
                    "code": self.entity_description.key,
                    "value": option,
                }
            ]
        )
