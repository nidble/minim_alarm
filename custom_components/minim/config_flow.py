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
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMED_VACATION,
    STATE_ALARM_DISARMED,
)
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


class BadRequest(HTTPException):
    "Enhance HttpExeception."

    pass


_LOGGER = logging.getLogger(__name__)

DEFAULT_SCENARIOS_SCHEMA = {
    STATE_ALARM_ARMED_AWAY: 0,
    STATE_ALARM_DISARMED: 1,
    STATE_ALARM_ARMED_NIGHT: 2,
    STATE_ALARM_ARMED_HOME: 3,
    STATE_ALARM_ARMED_VACATION: 0,
    # STATE_ALARM_ARMED_CUSTOM_BYPASS: 0,
}

PANEL_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_PANEL_NAME, description={"suggested_value": "Minim Alarm Panel"}
        ): cv.string,
        vol.Optional(
            STATE_ALARM_ARMED_AWAY, description={"suggested_value": 0}
        ): cv.positive_int,
        vol.Optional(
            STATE_ALARM_DISARMED, description={"suggested_value": 1}
        ): cv.positive_int,
        vol.Optional(
            STATE_ALARM_ARMED_NIGHT, description={"suggested_value": 2}
        ): cv.positive_int,
        vol.Optional(
            STATE_ALARM_ARMED_HOME, description={"suggested_value": 3}
        ): cv.positive_int,
        vol.Optional(
            STATE_ALARM_ARMED_VACATION, description={"suggested_value": 0}
        ): cv.positive_int,
        # vol.Optional(
        #     STATE_ALARM_ARMED_CUSTOM_BYPASS, description={"suggested_value": 0}
        # ): cv.positive_int,
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
    """Generate an unique_id suitable for this integration ."""
    return UNIQUE_ID_PREFIX + "_" + cv.slugify(s)


async def validate_panel(name: str) -> None:
    """Validate a Minim Panel."""

    # TODO: add some validation stuff
    return gen_unique_panel_id(name)


async def validate_auth(
    username: str,
    password: str,
    client_id: str,
    hass: core.HomeAssistant,  # or maybe hass: core.HassJob,
) -> None:
    """Validate a GitHub access token.

    Raises a ValueError if the auth token is invalid.
    """
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
        # except BadRequest as exc:
        raise ValueError("Something bad happened while validating Auth form") from exc

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
                # ----------------------------------------------------------------------------
                # Setting our unique id here just because we have the info at this stage to do that
                # and it will abort early on in the process if alreay setup.
                # You can put this in any step however.
                # ----------------------------------------------------------------------------
                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()

                # Set our title variable here for use later
                self._title = info["title"]

                # Input is valid, set data.
                self.data = user_input
                self.data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
                self.data[CONF_PANELS] = []
                # Return the form of the next step.
                return await self.async_step_panel()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_panel(self, user_input: Optional[dict[str, Any]] = None):
        """Second step in config flow to add a Panel."""
        errors: dict[str, str] = {}
        panel_unique_id = UNIQUE_ID_PREFIX
        if user_input is not None:
            # Validate the panel.
            try:
                panel_unique_id = await validate_panel(
                    user_input[CONF_PANEL_NAME] or CONST_ALARM_CONTROL_PANEL_NAME,
                )
                scenarios = {
                    STATE_ALARM_ARMED_AWAY: user_input.get(
                        STATE_ALARM_ARMED_AWAY,
                        DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_ARMED_AWAY],
                    ),
                    STATE_ALARM_DISARMED: user_input.get(
                        STATE_ALARM_DISARMED,
                        DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_DISARMED],
                    ),
                    STATE_ALARM_ARMED_NIGHT: user_input.get(
                        STATE_ALARM_ARMED_NIGHT,
                        DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_ARMED_NIGHT],
                    ),
                    STATE_ALARM_ARMED_HOME: user_input.get(
                        STATE_ALARM_ARMED_HOME,
                        DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_ARMED_HOME],
                    ),
                    STATE_ALARM_ARMED_VACATION: user_input.get(
                        STATE_ALARM_ARMED_VACATION,
                        DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_ARMED_VACATION],
                    ),
                    # STATE_ALARM_ARMED_CUSTOM_BYPASS: user_input.get(
                    #     STATE_ALARM_ARMED_CUSTOM_BYPASS,
                    #     DEFAULT_SCENARIOS_SCHEMA[STATE_ALARM_ARMED_CUSTOM_BYPASS],
                    # ),
                }
            except ValueError:
                errors["base"] = "invalid_panel"

            if not errors:
                # Input is valid, set data.
                self.data[CONF_PANELS].append(
                    {
                        "panel_name": user_input[CONF_PANEL_NAME],
                        "unique_id": panel_unique_id,
                        "scenarios": scenarios,
                    }
                )
                # If user ticked the box show this form again so they can add an
                # additional panel.
                if user_input.get("add_another", False):
                    return await self.async_step_panel()

                # User is done adding panels, create the config entry.
                return self.async_create_entry(title="Minim Alarm", data=self.data)

        return self.async_show_form(
            step_id="panel", data_schema=PANEL_SCHEMA, errors=errors
        )
