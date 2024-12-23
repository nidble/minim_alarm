"""Nintendo Wishlist integration."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging

from pyinim.inim_cloud import InimCloud as MinimCloud

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CLIENT_ID, CONF_DEVICE_ID, DOMAIN
from .types import MinimResult

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.ALARM_CONTROL_PANEL,
]


@dataclass
class RuntimeData:
    """Class to hold minim data."""

    coordinator: DataUpdateCoordinator
    inim_cloud_api: MinimCloud
    cancel_update_listener: Callable


async def async_setup_entry(
    hass: core.HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Set up Minim Integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    client_id = config_entry.data[CONF_CLIENT_ID]
    device_id = config_entry.data[CONF_DEVICE_ID]
    scan_interval = timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL])

    inim_cloud_api = MinimCloud(
        async_get_clientsession(hass),
        name="Minim",
        username=username,
        password=password,
        client_id=client_id,
    )

    async def async_fetch_minim() -> MinimResult | None:
        try:
            await inim_cloud_api.get_request_poll(device_id)
            _, _, res = await inim_cloud_api.get_devices_extended(device_id)
            return res
        except Exception as ex:
            # raise ConfigEntryAuthFailed("Credentials expired for Minim Cloud") from ex
            config_entry.async_start_reauth(hass)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name=DOMAIN,
        update_method=async_fetch_minim,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()
    # or
    # await coordinator.async_refresh()

    # ----------------------------------------------------------------------------
    # Test to see if api initialised correctly, else raise ConfigNotReady to make
    # HA retry setup.
    # Change this to match how your api will know if connected or successful
    # update.
    # ----------------------------------------------------------------------------
    if not coordinator.data:
        raise ConfigEntryNotReady

    # ----------------------------------------------------------------------------
    # Initialise a listener for config flow options changes.
    # This will be removed automatically if the integraiton is unloaded.
    # See config_flow for defining an options setting that shows up as configure
    # on the integration.
    # If you do not want any config flow options, no need to have listener.
    # ----------------------------------------------------------------------------
    cancel_update_listener = config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    # ----------------------------------------------------------------------------
    # Add the coordinator and update listener to hass data to make
    # accessible throughout your integration
    # Note: this will change on HA2024.6 to save on the config entry.
    # ----------------------------------------------------------------------------
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = RuntimeData(
        coordinator, inim_cloud_api, cancel_update_listener
    )

    # ----------------------------------------------------------------------------
    # Setup platforms (based on the list of entity types in PLATFORMS defined above)
    # This calls the async_setup method in each of your entity type files.
    # ----------------------------------------------------------------------------
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    # ----------------------------------------------------------------------------
    # Setup global services
    # This can be done here but included in a seperate file for ease of reading.
    # See also switch.py for entity services examples
    # ----------------------------------------------------------------------------
    # TODO: ExampleServicesSetup(hass, config_entry)

    # Return true to denote a successful setup.
    return True


async def _async_update_listener(hass: core.HomeAssistant, config_entry: ConfigEntry):
    """Handle config options update.

    Reload the integration when the options change.
    Called from our listener created above.
    """
    await hass.config_entries.async_reload(config_entry.entry_id)


# class MyCoordinator(DataUpdateCoordinator):
#     """My custom coordinator."""

#     def __init__(self, hass, my_api):
#         """Initialize my coordinator."""
#         super().__init__(
#             hass,
#             _LOGGER,
#             # Name of the data. For logging purposes.
#             name="My sensor",
#             # Polling interval. Will only be polled if there are subscribers.
#             update_interval=timedelta(seconds=30),
#         )
#         self.my_api = my_api

#     async def _async_update_data(self):
#         """Fetch data from API endpoint.

#         This is the place to pre-process the data to lookup tables
#         so entities can quickly look up their data.
#         """
#         try:
#             # Note: asyncio.TimeoutError and aiohttp.ClientError are already
#             # handled by the data update coordinator.
#             async with async_timeout.timeout(10):
#                 # Grab active context variables to limit data required to be fetched from API
#                 # Note: using context is not required if there is no need or ability to limit
#                 # data retrieved from API.
#                 listening_idx = set(self.async_contexts())
#                 return await self.my_api.fetch_data(listening_idx)
#         except ApiAuthError as err:
#             # Raising ConfigEntryAuthFailed will cancel future updates
#             # and start a config flow with SOURCE_REAUTH (async_step_reauth)
#             raise ConfigEntryAuthFailed from err
#         except ApiError as err:
#             raise UpdateFailed(f"Error communicating with API: {err}")
