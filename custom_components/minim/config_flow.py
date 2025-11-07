"""Support for MINIM Config Flow."""

from copy import deepcopy
from http.client import HTTPException
import logging
from typing import Any, Optional

from pyinim.inim_cloud import InimCloud as MinimCloud
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
# 🆕 Home Assistant 2025.x usa l'enum AlarmControlPanelState invece delle vecchie costanti
from homeassistant.components.alarm_control_panel import AlarmControlPanelState

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)

from .const import (
    CONF_PANEL_NAME,
    CONF_PANELS,
    CONST_ALARM_CONTROL_PANEL_NAME,
    CONST_MANUFACTURER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

UNIQUE_ID_PREFIX = "alarm_control_panel"

_LOGGER = logging.getLogger(__name__)


class BadRequest(HTTPException):
    """Enhance HttpException."""
    pass


# 🆕 Conversione enum -> valori numerici per i vari scenari
DEFAULT_SCENARIOS_SCHEMA = {
    AlarmControlPanelState.ARMED_AWAY.value: 0,
    AlarmControlPanelState.DISARMED.value: 1,
    AlarmControlPanelState.ARMED_NIGHT.value: 2,
    AlarmControlPanelState.ARMED_HOME.value: 3,
    AlarmControlPanelState.ARMED_VACATION.value: 0,
}


PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_PANEL_NAME, description={"suggested_value": "Minim Alarm Panel"}
        ): cv.string,
        vol.Optional(
            AlarmControlPanelState.ARMED_AWAY.value, description={"suggested_value": 0}
        ): cv.positive_int,
        vol.Optional(
            AlarmControlPanelState.DISARMED.value, description={"suggested_value": 1}
        ): cv.positive_int,
        vol.Optional(
            AlarmControlPanelState.ARMED_NIGHT.value, description={"suggested_value": 2}
        ): cv.positive_int,
        vol.Optional(
            AlarmControlPanelState.ARMED_HOME.value, description={"suggested_value": 3}
        ): cv.positive_int,
        vol.Optional(
            AlarmControlPanelState.ARMED_VACATION.value, description={"suggested_value": 0}
        ): cv.positive_int,
        vol.Optional("add_another"): cv.boolean,
    }
)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_CLIENT_ID): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)


def gen_unique_panel_id(s: str) -> str:
    """Generate an unique_id suitable for this integration."""
    return UNIQUE_ID_PREFIX + "_" + cv.slugify(s)


async def validate_panel(name: str) -> str:
    """Validate a Minim Panel."""
    return gen_unique_panel_id(name)


async def validate_auth(
    username: str,
    password: str,
    client_id: str,
    hass: core.HomeAssistant,
) -> dict[str, Any]:
    """Validate credentials for Minim Cloud."""
    session = async_get_clientsession(hass)
    minim = MinimCloud(
        session,
        name=CONST_MANUFACTURER,
        username=username,
        password=password,
        client_id=client_id,
    )

    try:
        await minim.token()
    except Exception as exc:
        raise ValueError("Authentication failed while validating Minim credentials") from exc

    return {"title": f"Minim Integration for - {username}"}


class MinimConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Minim config flow."""

    VERSION = 1
    data: Optional[dict[str, Any]]
    _title: str

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """User initiated a flow via the user interface."""
        errors: dict[str, str] = {}
        info = {}
        if user_input is not None:
            try:
                info = await validate_auth(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_CLIENT_ID],
                    self.hass,
                )
            except ValueError:
                errors["base"] = "auth"

            if not errors:
                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()

                self._title = info["title"]
                self.data = user_input
                self.data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
                self.data[CONF_PANELS] = []

                return await self.async_step_panel()

        return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)

    async def async_step_panel(self, user_input: Optional[dict[str, Any]] = None):
        """Second step in config flow to add a Panel."""
        errors: dict[str, str] = {}
        panel_unique_id = UNIQUE_ID_PREFIX

        if user_input is not None:
            try:
                panel_unique_id = await validate_panel(
                    user_input.get(CONF_PANEL_NAME) or CONST_ALARM_CONTROL_PANEL_NAME,
                )
                scenarios = {
                    AlarmControlPanelState.ARMED_AWAY.value: user_input.get(
                        AlarmControlPanelState.ARMED_AWAY.value,
                        DEFAULT_SCENARIOS_SCHEMA[AlarmControlPanelState.ARMED_AWAY.value],
                    ),
                    AlarmControlPanelState.DISARMED.value: user_input.get(
                        AlarmControlPanelState.DISARMED.value,
                        DEFAULT_SCENARIOS_SCHEMA[AlarmControlPanelState.DISARMED.value],
                    ),
                    AlarmControlPanelState.ARMED_NIGHT.value: user_input.get(
                        AlarmControlPanelState.ARMED_NIGHT.value,
                        DEFAULT_SCENARIOS_SCHEMA[AlarmControlPanelState.ARMED_NIGHT.value],
                    ),
                    AlarmControlPanelState.ARMED_HOME.value: user_input.get(
                        AlarmControlPanelState.ARMED_HOME.value,
                        DEFAULT_SCENARIOS_SCHEMA[AlarmControlPanelState.ARMED_HOME.value],
                    ),
                    AlarmControlPanelState.ARMED_VACATION.value: user_input.get(
                        AlarmControlPanelState.ARMED_VACATION.value,
                        DEFAULT_SCENARIOS_SCHEMA[AlarmControlPanelState.ARMED_VACATION.value],
                    ),
                }
            except ValueError:
                errors["base"] = "invalid_panel"

            if not errors:
                self.data[CONF_PANELS].append(
                    {
                        "panel_name": user_input[CONF_PANEL_NAME],
                        "unique_id": panel_unique_id,
                        "scenarios": scenarios,
                    }
                )

                if user_input.get("add_another", False):
                    return await self.async_step_panel()

                return self.async_create_entry(title="Minim Alarm", data=self.data)

        return self.async_show_form(step_id="panel", data_schema=PANEL_SCHEMA, errors=errors)

