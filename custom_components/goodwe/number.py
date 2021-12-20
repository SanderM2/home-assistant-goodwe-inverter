"""GoodWe PV inverter numeric settings entities."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from goodwe import Inverter, InverterError

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import ENTITY_CATEGORY_CONFIG, PERCENTAGE, POWER_WATT
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, KEY_DEVICE_INFO, KEY_INVERTER

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoodweNumberEntityDescription(NumberEntityDescription):
    """Class describing Goodwe sensor entities."""

    getter: Callable[[Inverter], Awaitable[int]] | None = None
    setter: Callable[[Inverter, int], Awaitable[None]] | None = None


NUMBERS = (
    GoodweNumberEntityDescription(
        key="grid_export_limit",
        name="Grid export limit",
        icon="mdi:transmission-tower",
        entity_category=ENTITY_CATEGORY_CONFIG,
        unit_of_measurement=POWER_WATT,
        getter=lambda inv: inv.get_grid_export_limit(),
        setter=lambda inv, val: inv.set_grid_export_limit(val),
    ),
    GoodweNumberEntityDescription(
        key="battery_discharge_depth",
        name="Depth of discharge (on-grid)",
        icon="mdi:battery-arrow-down",
        entity_category=ENTITY_CATEGORY_CONFIG,
        unit_of_measurement=PERCENTAGE,
        getter=lambda inv: inv.get_ongrid_battery_dod(),
        setter=lambda inv, val: inv.set_ongrid_battery_dod(val),
    ),
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the inverter select entities from a config entry."""
    inverter = hass.data[DOMAIN][config_entry.entry_id][KEY_INVERTER]
    device_info = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE_INFO]

    entities = []

    for description in NUMBERS:
        try:
            current_value = await description.getter(inverter)
            entity = InverterNumberEntity(device_info, description, inverter, current_value)
            if description.key == "grid_export_limit":
                entity._attr_max_value = 10000
                entity._attr_min_value = 0
                entity._attr_step = 100
            if description.key == "battery_discharge_depth":
                entity._attr_max_value = 99
                entity._attr_min_value = 0
                entity._attr_step = 1

            entities.append(entity)
        except InverterError:
            # Inverter model does not support this setting
            _LOGGER.debug("Could not read inverter setting %s", description.key)

    async_add_entities(entities)

    return True


class InverterNumberEntity(NumberEntity):
    """Inverter numeric setting entity."""

    _attr_should_poll = False
    entity_description: GoodweNumberEntityDescription

    def __init__(
        self,
        device_info: DeviceInfo,
        description: GoodweNumberEntityDescription,
        inverter: Inverter,
        current_value: int,
    ) -> None:
        """Initialize the number inverter setting entity."""
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}-{description.key}-{inverter.serial_number}"
        self._attr_device_info = device_info
        self._attr_value = float(current_value)
        self._inverter: Inverter = inverter

    async def async_set_value(self, value: float) -> None:
        """Set new value."""
        if self.entity_description.setter:
            await self.entity_description.setter(self._inverter, int(value))
        self._attr_value = float(value)
        self.async_write_ha_state()
