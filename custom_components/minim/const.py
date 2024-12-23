"""Component level custom constants."""

from datetime import timedelta
from typing import Final

DOMAIN = "minim"

CONF_CLIENT_ID: Final = "client_id"
CONF_DEVICE_ID: Final = "device_id"
CONF_SCENARIOS: Final = "scenarios"
CONF_PANELS: Final = "panels"
CONF_PANEL_NAME: Final = "panel_name"
CONST_ALARM_CONTROL_PANEL_NAME: Final = "Alarm Panel"
CONST_MANUFACTURER: Final = "Minim"

# CONNECTION: Final = "connection"

# from homeassistant.components.binary_sensor import (SCAN_INTERVAL as DEFAULT_SCAN_INTERVAL)
# DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)
DEFAULT_SCAN_INTERVAL = 30
