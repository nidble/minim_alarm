import logging

from homeassistant import core
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import slugify

from .const import CONF_DEVICE_ID, CONST_MANUFACTURER, DOMAIN
from .types import Device, MinimResult, Zone

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Binary Sensors."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    device_id = config_entry.data[CONF_DEVICE_ID]
    res: Device = coordinator.data.Data[device_id]

    binary_sensors = [
        MinimBinarySensorEntity(coordinator, zone, device_id) for zone in res.Zones
    ]

    # Create the binary sensors.
    async_add_entities(binary_sensors)


class MinimBinarySensorEntity(CoordinatorEntity, BinarySensorEntity):
    """Represents a Presense Sensor for every Zone."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator[MinimResult],
        zone: Zone,
        device_id: str,
    ):
        super().__init__(coordinator, context=zone.ZoneId)

        self._zone = zone
        self._device_id = device_id
        self.attrs = {}
        self._attr_extra_state_attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, zone.ZoneId)},
            manufacturer=CONST_MANUFACTURER,
            model=zone.Type,
            name=zone.Name,
        )
        self._attr_unique_id = self.get_unique_id()

    # @property
    # def icon(self):
    #     """Icon to use in the frontend."""
    #     return "mdi:nintendo-switch"

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        zones: list[Zone] = self.coordinator.data.Data[self._device_id].Zones
        for zone in zones:
            if zone.ZoneId == self._zone.ZoneId:
                return zone.Status == 2
        return False

    # @property
    # def entity_id(self) -> str:
    def get_unique_id(self) -> str:
        """Retrieve the sensor unique id."""
        slug = slugify(self._zone.Name)
        return f"binary_sensor.minim_{slug}_{self._zone.ZoneId}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._zone.Name

    # @property
    # def extra_state_attributes(self):
    #     return {"matches": self.matches}

    # code example:
    # @core.callback
    # def on_off_state_updated(self, state: bool, **kwargs: Any) -> None:
    #     """Handle state updates."""
    #     self._on_off_state = state

    #     if self._delay_listener is not None:
    #         self._delay_listener()
    #         self._delay_listener = None

    #     off_delay = self._tasmota_entity.off_delay
    #     if self._on_off_state and off_delay is not None:
    #         self._delay_listener = evt.async_call_later(
    #             self.hass, off_delay, self.off_delay_listener
    #         )

    #     self.async_write_ha_state()
