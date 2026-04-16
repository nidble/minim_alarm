import logging

from homeassistant import core
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import slugify

from pyinim.inim_cloud import InimCloud as MinimCloud

from .const import CONF_DEVICE_ID, CONST_MANUFACTURER, DOMAIN
from .types import Device, MinimResult, Zone

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Switches."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    device_id = config_entry.data[CONF_DEVICE_ID]
    res: Device = coordinator.data.Data[device_id]
    inim_cloud_api = hass.data[DOMAIN][config_entry.entry_id].inim_cloud_api

    switches = [
        MinimSwitchEntity(coordinator, inim_cloud_api, zone, device_id) for zone in res.Zones
    ]

    # Create the switch
    async_add_entities(switches)


class MinimSwitchEntity(CoordinatorEntity, SwitchEntity):
    """
      Represents a Bypass Switch for every Zone.
      True if it is not bypassed.
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[MinimResult],
        inim_cloud_api: MinimCloud,
        zone: Zone,
        device_id: str,
    ):
        super().__init__(coordinator, context=zone.ZoneId)

        self._zone = zone
        self._device_id = device_id
        self._cloud_api = inim_cloud_api
        self.attrs = {}
        self._attr_extra_state_attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, zone.ZoneId)},
            manufacturer=CONST_MANUFACTURER,
            model=zone.Type,
            name=zone.Name,
        )
        self._attr_unique_id = self.get_unique_id()

    @property
    def is_on(self):
        """Return if it is not bypassed"""
        zones: list[Zone] = self.coordinator.data.Data[self._device_id].Zones
        for zone in zones:
            if zone.ZoneId == self._zone.ZoneId:
                return zone.Bypassed == 0
        return False

    def get_unique_id(self) -> str:
        slug = slugify(self._zone.Name)
        return f"switch.minim_{slug}_{self._zone.ZoneId}"

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._zone.Name

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._cloud_api.get_bypass_mode(self._device_id, self._zone.ZoneId, True)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._cloud_api.get_bypass_mode(self._device_id, self._zone.ZoneId, False)
