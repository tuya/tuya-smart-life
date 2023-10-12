"""Support for smartlife devices."""
from typing import NamedTuple, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.const import __version__
from homeassistant.loader import async_get_integration

from .const import (
    DOMAIN,
    LOGGER,
    CONF_CLIENT_ID,
    PLATFORMS,
    DPCode,
    SMART_LIFE_HA_SIGNAL_UPDATE_ENTITY,
    SMART_LIFE_DISCOVERY_NEW
)

from tuya_sharing import Manager, SharingDeviceListener, CustomerDevice, SharingTokenListener
from tuya_sharing import logger

logger.setLevel(LOGGER.getEffectiveLevel())


class HomeAssistantSmartLifeData(NamedTuple):
    """Smart Life data stored in the Home Assistant data object."""

    manager: Manager
    listener: SharingDeviceListener


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""
    hass.data.setdefault(DOMAIN, {})

    if hass.data[DOMAIN].get(entry.entry_id) is None:
        token_listener = TokenListener(hass, entry)
        smart_life_manager = Manager(
            CONF_CLIENT_ID,
            entry.data["user_code"],
            entry.data["terminal_id"],
            entry.data["endpoint"],
            entry.data["token_info"],
            token_listener
        )

        listener = DeviceListener(hass, smart_life_manager)
        smart_life_manager.add_device_listener(listener)
        hass.data[DOMAIN][entry.entry_id] = HomeAssistantSmartLifeData(
            manager=smart_life_manager,
            listener=listener
        )
    else:
        hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]
        smart_life_manager = hass_data.manager

    integration = await async_get_integration(hass, DOMAIN)
    manifest = integration.manifest
    smart_life_version = manifest["version"]
    sdk_version = manifest["requirements"]
    sharing_sdk = ""
    for item in sdk_version:
        if "device-sharing-sdk" in item:
            sharing_sdk = item.split("==")[1]
    await hass.async_add_executor_job(smart_life_manager.report_version, __version__, smart_life_version, sharing_sdk)

    # Get devices & clean up device entities
    await hass.async_add_executor_job(smart_life_manager.update_device_cache)
    await cleanup_device_registry(hass, smart_life_manager)

    # Migrate old unique_ids to the new format
    async_migrate_entities_unique_ids(hass, entry, smart_life_manager)

    device_registry = dr.async_get(hass)
    for device in smart_life_manager.device_map.values():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device.id)},
            manufacturer="smartlife",
            name=device.name,
            model=f"{device.product_name} (unsupported)",
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await hass.async_add_executor_job(smart_life_manager.refresh_mq)
    return True


async def cleanup_device_registry(
        hass: HomeAssistant, device_manager: Manager
) -> None:
    """Remove deleted device registry entry if there are no remaining entities."""
    device_registry = dr.async_get(hass)
    for dev_id, device_entry in list(device_registry.devices.items()):
        for item in device_entry.identifiers:
            if item[0] == DOMAIN and item[1] not in device_manager.device_map:
                device_registry.async_remove_device(dev_id)
                break


@callback
def async_migrate_entities_unique_ids(
        hass: HomeAssistant, config_entry: ConfigEntry, device_manager: Manager
) -> None:
    """Migrate unique_ids in the entity registry to the new format."""
    entity_registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    light_entries = {
        entry.unique_id: entry
        for entry in registry_entries
        if entry.domain == LIGHT_DOMAIN
    }
    switch_entries = {
        entry.unique_id: entry
        for entry in registry_entries
        if entry.domain == SWITCH_DOMAIN
    }

    for device in device_manager.device_map.values():
        # Old lights where in `smartlife.{device_id}` format, now the DPCode is added.
        #
        # If the device is a previously supported light category and still has
        # the old format for the unique ID, migrate it to the new format.
        #
        # Previously only devices providing the SWITCH_LED DPCode were supported,
        # thus this can be added to those existing IDs.
        #
        # `smartlife.{device_id}` -> `smartlife.{device_id}{SWITCH_LED}`
        if (
                device.category in ("dc", "dd", "dj", "fs", "fwl", "jsq", "xdd", "xxj")
                and (entry := light_entries.get(f"smartlife.{device.id}"))
                and f"smartlife.{device.id}{DPCode.SWITCH_LED}" not in light_entries
        ):
            entity_registry.async_update_entity(
                entry.entity_id, new_unique_id=f"smartlife.{device.id}{DPCode.SWITCH_LED}"
            )

        # Old switches has different formats for the unique ID, but is mappable.
        #
        # If the device is a previously supported switch category and still has
        # the old format for the unique ID, migrate it to the new format.
        #
        # `smartlife.{device_id}` -> `smartlife.{device_id}{SWITCH}`
        # `smartlife.{device_id}_1` -> `smartlife.{device_id}{SWITCH_1}`
        # ...
        # `smartlife.{device_id}_6` -> `smartlife.{device_id}{SWITCH_6}`
        # `smartlife.{device_id}_usb1` -> `smartlife.{device_id}{SWITCH_USB1}`
        # ...
        # `smartlife.{device_id}_usb6` -> `smartlife.{device_id}{SWITCH_USB6}`
        #
        # In all other cases, the unique ID is not changed.
        if device.category in ("bh", "cwysj", "cz", "dlq", "kg", "kj", "pc", "xxj"):
            for postfix, dpcode in (
                    ("", DPCode.SWITCH),
                    ("_1", DPCode.SWITCH_1),
                    ("_2", DPCode.SWITCH_2),
                    ("_3", DPCode.SWITCH_3),
                    ("_4", DPCode.SWITCH_4),
                    ("_5", DPCode.SWITCH_5),
                    ("_6", DPCode.SWITCH_6),
                    ("_usb1", DPCode.SWITCH_USB1),
                    ("_usb2", DPCode.SWITCH_USB2),
                    ("_usb3", DPCode.SWITCH_USB3),
                    ("_usb4", DPCode.SWITCH_USB4),
                    ("_usb5", DPCode.SWITCH_USB5),
                    ("_usb6", DPCode.SWITCH_USB6),
            ):
                if (
                        entry := switch_entries.get(f"smartlife.{device.id}{postfix}")
                ) and f"smartlife.{device.id}{dpcode}" not in switch_entries:
                    entity_registry.async_update_entity(
                        entry.entity_id, new_unique_id=f"smartlife.{device.id}{dpcode}"
                    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading the smartlife platforms."""

    LOGGER.debug("unload entry id = %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    LOGGER.debug("remove entry id = %s", entry.entry_id)
    hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]

    if hass_data.manager.mq is not None:
        hass_data.manager.mq.stop()
    hass_data.manager.remove_device_listener(hass_data.listener)
    await hass.async_add_executor_job(hass_data.manager.unload)
    hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    pass


class DeviceListener(SharingDeviceListener):
    """Device Update Listener."""

    def __init__(
            self,
            hass: HomeAssistant,
            manager: Manager,
    ) -> None:
        """Init DeviceListener."""
        self.hass = hass
        self.manager = manager

    def update_device(self, device: CustomerDevice) -> None:
        """Update device status."""
        LOGGER.debug(
            "Received update for device %s: %s",
            device.id,
            self.manager.device_map[device.id].status,
        )
        dispatcher_send(self.hass, f"{SMART_LIFE_HA_SIGNAL_UPDATE_ENTITY}_{device.id}")

    def add_device(self, device: CustomerDevice) -> None:
        """Add device added listener."""
        # Ensure the device isn't present stale
        self.hass.add_job(self.async_remove_device, device.id)

        dispatcher_send(self.hass, SMART_LIFE_DISCOVERY_NEW, [device.id])

    def remove_device(self, device_id: str) -> None:
        """Add device removed listener."""
        self.hass.add_job(self.async_remove_device, device_id)

    @callback
    def async_remove_device(self, device_id: str) -> None:
        """Remove device from Home Assistant."""
        LOGGER.debug("Remove device: %s", device_id)
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_id)}
        )
        if device_entry is not None:
            device_registry.async_remove_device(device_entry.id)


class TokenListener(SharingTokenListener):
    def __init__(
            self,
            hass: HomeAssistant,
            entry: ConfigEntry,
    ) -> None:
        """Init TokenListener."""
        self.hass = hass
        self.entry = entry

    def update_token(self, token_info: [str, Any]):
        data = {**self.entry.data, "token_info": token_info}
        LOGGER.debug("update token info : %s", data)
        self.hass.config_entries.async_update_entry(self.entry, data=data)
