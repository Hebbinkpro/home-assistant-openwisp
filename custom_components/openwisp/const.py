"""Constants for openwisp."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "openwisp"

CONF_ORGANIZATION = "organization"

UPDATE_INTERVAL = timedelta(minutes=1)

# how long a Wi-Fi client may be missing from the open sessions before it is
# reported away, so that roaming between devices does not flap
CONSIDER_HOME = timedelta(minutes=3)
