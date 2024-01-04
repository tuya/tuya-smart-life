"""Support for smartlife sensors."""
from __future__ import annotations

from dataclasses import dataclass

from tuya_sharing import Manager, CustomerDevice
from tuya_sharing.device import DeviceStatusRange


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HomeAssistantSmartLifeData
from .base import ElectricityTypeData, EnumTypeData, IntegerTypeData, SmartLifeEntity
from .const import (
    DEVICE_CLASS_UNITS,
    DOMAIN,
    SMART_LIFE_DISCOVERY_NEW,
    DPCode,
    DPType,
    UnitOfMeasurement,
)


@dataclass
class SmartLifeSensorEntityDescription(SensorEntityDescription):
    """Describes Smart Life sensor entity."""

    subkey: str | None = None


# Commonly used battery sensors, that are re-used in the sensors down below.
BATTERY_SENSORS: tuple[SmartLifeSensorEntityDescription, ...] = (
    SmartLifeSensorEntityDescription(
        key=DPCode.BATTERY_PERCENTAGE,
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartLifeSensorEntityDescription(
        key=DPCode.BATTERY_STATE,
        name="Battery state",
        icon="mdi:battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartLifeSensorEntityDescription(
        key=DPCode.BATTERY_VALUE,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartLifeSensorEntityDescription(
        key=DPCode.VA_BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

# All descriptions can be found here. Mostly the Integer data types in the
# default status set of each category (that don't have a set instruction)
# end up being a sensor.
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
SENSORS: dict[str, tuple[SmartLifeSensorEntityDescription, ...]] = {
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.GAS_SENSOR_VALUE,
            name="Gas",
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH4_SENSOR_VALUE,
            name="Methane",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VOC_VALUE,
            name="Volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25_VALUE,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO_VALUE,
            name="Carbon monoxide",
            icon="mdi:molecule-co",
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            icon="mdi:molecule-co2",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH2O_VALUE,
            name="Formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.BRIGHT_STATE,
            name="Luminosity",
            icon="mdi:brightness-6",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.BRIGHT_VALUE,
            name="Luminosity",
            icon="mdi:brightness-6",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SMOKE_SENSOR_VALUE,
            name="Smoke amount",
            icon="mdi:smoke-detector",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smart Kettle
    # https://developer.tuya.com/en/docs/iot/fbh?id=K9gf484m21yq7
    "bh": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Current temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT_F,
            name="Current temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.STATUS,
            name="Status",
        ),
    ),
    # CO2 Detector
    # https://developer.tuya.com/en/docs/iot/categoryco2bj?id=Kaiuz3wes7yuy
    "co2bj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Two-way temperature and humidity switch
    # "MOES Temperature and Humidity Smart Switch Module MS-103"
    # Documentation not found
    "wkcz": (
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # CO Detector
    # https://developer.tuya.com/en/docs/iot/categorycobj?id=Kaiuz3u1j6q1v
    "cobj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CO_VALUE,
            name="Carbon monoxide",
            device_class=SensorDeviceClass.CO,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    "cwwsq": (
        SmartLifeSensorEntityDescription(
            key=DPCode.FEED_REPORT,
            name="Last amount",
            icon="mdi:counter",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Air Quality Monitor
    # No specification on Tuya portal
    "hjjcy": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH2O_VALUE,
            name="Formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VOC_VALUE,
            name="Volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25_VALUE,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Formaldehyde Detector
    # Note: Not documented
    "jqbj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VOC_VALUE,
            name="Volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25_VALUE,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_HUMIDITY,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH2O_VALUE,
            name="Formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Methane Detector
    # https://developer.tuya.com/en/docs/iot/categoryjwbj?id=Kaiuz40u98lkm
    "jwbj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CH4_SENSOR_VALUE,
            name="Methane",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
    ),
    # IoT Switch
    # Note: Undocumented
    "tdq": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        ),
    ),
    # Luminance Sensor
    # https://developer.tuya.com/en/docs/iot/categoryldcg?id=Kaiuz3n7u69l8
    "ldcg": (
        SmartLifeSensorEntityDescription(
            key=DPCode.BRIGHT_STATE,
            name="Luminosity",
            icon="mdi:brightness-6",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.BRIGHT_VALUE,
            name="Luminosity",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Door and Window Controller
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r5zjsy9
    "mc": BATTERY_SENSORS,
    # Door Window Sensor
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48hm02l8m
    "mcs": BATTERY_SENSORS,
    # Sous Vide Cooker
    # https://developer.tuya.com/en/docs/iot/categorymzj?id=Kaiuz2vy130ux
    "mzj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Current temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.STATUS,
            name="Status",
            translation_key="status",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.REMAIN_TIME,
            name="Remaining time",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            icon="mdi:timer",
        ),
    ),
    # PIR Detector
    # https://developer.tuya.com/en/docs/iot/categorypir?id=Kaiuz3ss11b80
    "pir": BATTERY_SENSORS,
    # PM2.5 Sensor
    # https://developer.tuya.com/en/docs/iot/categorypm25?id=Kaiuz3qof3yfu
    "pm2.5": (
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25_VALUE,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH2O_VALUE,
            name="Formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VOC_VALUE,
            name="Volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM1,
            name="Particulate matter 1.0 µm",
            device_class=SensorDeviceClass.PM1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM10,
            name="Particulate matter 10.0 µm",
            device_class=SensorDeviceClass.PM10,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    "qn": (
        SmartLifeSensorEntityDescription(
            key=DPCode.WORK_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Gas Detector
    # https://developer.tuya.com/en/docs/iot/categoryrqbj?id=Kaiuz3d162ubw
    "rqbj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.GAS_SENSOR_VALUE,
            icon="mdi:gas-cylinder",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Water Detector
    # https://developer.tuya.com/en/docs/iot/categorysj?id=Kaiuz3iub2sli
    "sj": BATTERY_SENSORS,
    # Emergency Button
    # https://developer.tuya.com/en/docs/iot/categorysos?id=Kaiuz3oi6agjy
    "sos": BATTERY_SENSORS,
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        SmartLifeSensorEntityDescription(
            key=DPCode.SENSOR_TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SENSOR_HUMIDITY,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.WIRELESS_ELECTRICITY,
            name="Battery",
            device_class=SensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Fingerbot
    "szjqr": BATTERY_SENSORS,
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    "tyndj": BATTERY_SENSORS,
    # Volatile Organic Compound Sensor
    # Note: Undocumented in cloud API docs, based on test device
    "voc": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CO2_VALUE,
            name="Carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25_VALUE,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CH2O_VALUE,
            name="Formaldehyde",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VOC_VALUE,
            name="Volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Thermostatic Radiator Valve
    # Not documented
    "wkf": BATTERY_SENSORS,
    # Temperature and Humidity Sensor
    # https://developer.tuya.com/en/docs/iot/categorywsdcg?id=Kaiuz3hinij34
    "wsdcg": (
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_HUMIDITY,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_VALUE,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.BRIGHT_VALUE,
            name="Luminosity",
            device_class=SensorDeviceClass.ILLUMINANCE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Pressure Sensor
    # https://developer.tuya.com/en/docs/iot/categoryylcg?id=Kaiuz3kc2e4gm
    "ylcg": (
        SmartLifeSensorEntityDescription(
            key=DPCode.PRESSURE_VALUE,
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Smoke Detector
    # https://developer.tuya.com/en/docs/iot/categoryywbj?id=Kaiuz3f6sf952
    "ywbj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.SMOKE_SENSOR_VALUE,
            name="Smoke amount",
            icon="mdi:smoke-detector",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *BATTERY_SENSORS,
    ),
    # Vibration Sensor
    # https://developer.tuya.com/en/docs/iot/categoryzd?id=Kaiuz3a5vrzno
    "zd": BATTERY_SENSORS,
    # Smart Electricity Meter
    # https://developer.tuya.com/en/docs/iot/smart-meter?id=Kaiuz4gv6ack7
    "zndb": (
        SmartLifeSensorEntityDescription(
            key=DPCode.FORWARD_ENERGY_TOTAL,
            name="Total energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
    ),
    # Circuit Breaker
    # https://developer.tuya.com/en/docs/iot/dlq?id=Kb0kidk9enyh8
    "dlq": (
        SmartLifeSensorEntityDescription(
            key=DPCode.FORWARD_ENERGY_TOTAL,
            name="Total energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_A,
            name="Phase A voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_B,
            name="Phase B voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C current",
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            subkey="electriccurrent",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            subkey="power",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PHASE_C,
            name="Phase C voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            subkey="voltage",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.ADD_ELE,
            name="add ele",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            entity_registry_enabled_default=True,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_CURRENT,
            name="Current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_POWER,
            name="Power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CUR_VOLTAGE,
            name="Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        SmartLifeSensorEntityDescription(
            key=DPCode.CLEAN_AREA,
            name="Cleaning area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.CLEAN_TIME,
            name="Cleaning time",
            icon="mdi:progress-clock",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TOTAL_CLEAN_AREA,
            name="Total cleaning area",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TOTAL_CLEAN_TIME,
            name="Total cleaning time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TOTAL_CLEAN_COUNT,
            name="Total cleaning times",
            icon="mdi:counter",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.DUSTER_CLOTH,
            name="Duster cloth life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.EDGE_BRUSH,
            name="Side brush life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.FILTER_LIFE,
            name="Filter life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.ROLL_BRUSH,
            name="Rolling brush life",
            icon="mdi:ticket-percent-outline",
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Curtain
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qy7wkre
    "cl": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TIME_TOTAL,
            name="Last operation duration",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:progress-clock",
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48qwjz0i3
    "jsq": (
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_CURRENT,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT_F,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.LEVEL_CURRENT,
            name="Water level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:waves-arrow-up",
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r41mn81
    "kj": (
        SmartLifeSensorEntityDescription(
            key=DPCode.FILTER,
            name="Filter utilization",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:ticket-percent-outline",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.PM25,
            name="Particulate matter 2.5 µm",
            device_class=SensorDeviceClass.PM25,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:molecule",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TVOC,
            name="Total volatile organic compound",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.ECO2,
            name="Concentration of carbon dioxide",
            device_class=SensorDeviceClass.CO2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TOTAL_TIME,
            name="Total operating time",
            icon="mdi:history",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.TOTAL_PM,
            name="Total absorption of particles",
            icon="mdi:texture-box",
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.AIR_QUALITY,
            name="Air quality",
            icon="mdi:air-filter",
            translation_key="air_quality",
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48quojr54
    "fs": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_CURRENT,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # eMylo Smart WiFi IR Remote
    "wnykq": (
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_TEMPERATURE,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.VA_HUMIDITY,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf48r6jke8e
    "cs": (
        SmartLifeSensorEntityDescription(
            key=DPCode.TEMP_INDOOR,
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.HUMIDITY_INDOOR,
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    # Button or Multi-button device
    # https://developer.tuya.com/en/docs/iot/f?id=Kbeoa30s4fcdf
    "wxkg": (
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_1,
            name="Button 1",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_2,
            name="Button 2",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_3,
            name="Button 3",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_4,
            name="Button 4",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_5,
            name="Button 5",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_6,
            name="Button 6",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_7,
            name="Button 7",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_8,
            name="Button 8",
            icon="mdi:gesture-tap-button",
        ),
        SmartLifeSensorEntityDescription(
            key=DPCode.SWITCH_MODE_9,
            name="Button 9",
            icon="mdi:gesture-tap-button",
        ),
        *BATTERY_SENSORS,
    ),
}

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["cz"] = SENSORS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
SENSORS["pc"] = SENSORS["kg"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Smart Life sensor dynamically through Smart Life discovery."""
    hass_data: HomeAssistantSmartLifeData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Smart Life sensor."""
        entities: list[SmartLifeSensorEntity] = []
        for device_id in device_ids:
            device = hass_data.manager.device_map[device_id]
            if descriptions := SENSORS.get(device.category):
                for description in descriptions:
                    if description.key in device.status:
                        entities.append(
                            SmartLifeSensorEntity(
                                device, hass_data.manager, description
                            )
                        )

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SMART_LIFE_DISCOVERY_NEW, async_discover_device)
    )


class SmartLifeSensorEntity(SmartLifeEntity, SensorEntity):
    """Smart Life Sensor Entity."""

    entity_description: SmartLifeSensorEntityDescription

    _status_range: DeviceStatusRange | None = None
    _type: DPType | None = None
    _type_data: IntegerTypeData | EnumTypeData | None = None
    _uom: UnitOfMeasurement | None = None

    def __init__(
        self,
        device: CustomerDevice,
        device_manager: Manager,
        description: SmartLifeSensorEntityDescription,
    ) -> None:
        """Init Smart Life sensor."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = (
            f"{super().unique_id}{description.key}{description.subkey or ''}"
        )

        if int_type := self.find_dpcode(description.key, dptype=DPType.INTEGER):
            self._type_data = int_type
            self._type = DPType.INTEGER
            if description.native_unit_of_measurement is None:
                self._attr_native_unit_of_measurement = int_type.unit
        elif enum_type := self.find_dpcode(
            description.key, dptype=DPType.ENUM, prefer_function=True
        ):
            self._type_data = enum_type
            self._type = DPType.ENUM
        else:
            self._type = self.get_dptype(DPCode(description.key))

        # Logic to ensure the set device class and API received Unit Of Measurement
        # match Home Assistants requirements.
        if (
            self.device_class is not None
            and not self.device_class.startswith(DOMAIN)
            and description.native_unit_of_measurement is None
        ):
            # We cannot have a device class, if the UOM isn't set or the
            # device class cannot be found in the validation mapping.
            if (
                self.native_unit_of_measurement is None
                or self.device_class not in DEVICE_CLASS_UNITS
            ):
                self._attr_device_class = None
                return

            uoms = DEVICE_CLASS_UNITS[self.device_class]
            self._uom = uoms.get(self.native_unit_of_measurement) or uoms.get(
                self.native_unit_of_measurement.lower()
            )

            # Unknown unit of measurement, device class should not be used.
            if self._uom is None:
                self._attr_device_class = None
                return

            # If we still have a device class, we should not use an icon
            if self.device_class:
                self._attr_icon = None

            # Found unit of measurement, use the standardized Unit
            # Use the target conversion unit (if set)
            self._attr_native_unit_of_measurement = (
                self._uom.conversion_unit or self._uom.unit
            )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        # Only continue if data type is known
        if self._type not in (
            DPType.INTEGER,
            DPType.STRING,
            DPType.ENUM,
            DPType.JSON,
            DPType.RAW,
        ):
            return None

        # Raw value
        value = self.device.status.get(self.entity_description.key)
        if value is None:
            return None

        # Scale integer/float value
        if isinstance(self._type_data, IntegerTypeData):
            scaled_value = self._type_data.scale_value(value)
            if self._uom and self._uom.conversion_fn is not None:
                return self._uom.conversion_fn(scaled_value)
            return scaled_value

        # Unexpected enum value
        if (
            isinstance(self._type_data, EnumTypeData)
            and value not in self._type_data.range
        ):
            return None

        # Get subkey value from Json string.
        if self._type is DPType.JSON:
            if self.entity_description.subkey is None:
                return None
            values = ElectricityTypeData.from_json(value)
            return getattr(values, self.entity_description.subkey)

        if self._type is DPType.RAW:
            if self.entity_description.subkey is None:
                return None
            values = ElectricityTypeData.from_raw(value)
            return getattr(values, self.entity_description.subkey)

        # Valid string or enum value
        return value
